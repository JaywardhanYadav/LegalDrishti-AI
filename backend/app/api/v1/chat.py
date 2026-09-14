import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.core.security_guard import validate_and_sanitize_query
from app.core.upload import compute_sha256, save_vault_file, validate_upload
from app.models.chat import ChatMessage, ChatSession
from app.models.document import Document
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDocumentResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatTranscriptResponse,
)
from app.schemas.research import LegalResearchRequest
from app.services.extraction import extract_document_text
from app.services.research import perform_legal_research
from app.services.retrieval import generate_grounded_legal_answer

chat_router = APIRouter(prefix="/chat", tags=["Chat & Consultations"])


def _parse_sources(sources_raw: str | None) -> list[str]:
    if not sources_raw:
        return []
    try:
        parsed = json.loads(sources_raw)
        if isinstance(parsed, list):
            return [str(s) for s in parsed]
        return [str(parsed)]
    except Exception:
        return [s.strip() for s in sources_raw.split(",") if s.strip()]


@chat_router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List all consultation sessions for the logged-in user",
)
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionListResponse:
    stmt = (
        select(
            ChatSession,
            func.count(ChatMessage.id).label("messages_count")
        )
        .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.user_id == current_user.id)
        .group_by(ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    session_items = []
    for chat_session, msg_count in rows:
        item = ChatSessionResponse(
            id=chat_session.id,
            user_id=chat_session.user_id,
            case_id=chat_session.case_id,
            title=chat_session.title,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            messages_count=msg_count or 0,
        )
        session_items.append(item)

    return ChatSessionListResponse(
        sessions=session_items,
        total=len(session_items),
    )


@chat_router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new consultation session",
)
async def create_chat_session(
    payload: ChatSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionResponse:
    now_utc = datetime.now(timezone.utc)
    new_session = ChatSession(
        user_id=current_user.id,
        title=payload.title or "New Chat",
        case_id=payload.case_id,
        created_at=now_utc,
        updated_at=now_utc,
    )
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)

    return ChatSessionResponse(
        id=new_session.id,
        user_id=new_session.user_id,
        case_id=new_session.case_id,
        title=new_session.title,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at,
        messages_count=0,
    )


@chat_router.get(
    "/sessions/{session_id}",
    response_model=ChatTranscriptResponse,
    summary="Get full conversation transcript for a session",
)
async def get_chat_transcript(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatTranscriptResponse:
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    res = await session.execute(stmt)
    chat_session = res.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation session not found",
        )

    msg_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    msg_res = await session.execute(msg_stmt)
    messages = msg_res.scalars().all()

    formatted_messages = [
        ChatMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            sources=_parse_sources(m.sources),
            token_count=m.token_count,
            created_at=m.created_at,
        )
        for m in messages
    ]

    formatted_docs = []
    try:
        doc_stmt = (
            select(Document)
            .where(
                Document.session_id == session_id,
                Document.user_id == current_user.id,
            )
            .order_by(Document.created_at.asc())
        )
        doc_res = await session.execute(doc_stmt)
        session_docs = doc_res.scalars().all()

        formatted_docs = [
            ChatSessionDocumentResponse(
                id=d.id,
                title=d.title,
                file_name=d.file_name,
                file_size_bytes=d.file_size_bytes,
                created_at=d.created_at,
            )
            for d in session_docs
        ]
    except Exception as doc_err:
        pass

    return ChatTranscriptResponse(
        session_id=chat_session.id,
        title=chat_session.title,
        case_id=chat_session.case_id,
        messages=formatted_messages,
        documents=formatted_docs,
    )


@chat_router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    summary="Send legal prompt in session and receive synthesized answer",
)
async def send_chat_message(
    session_id: int,
    payload: ChatMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatMessageResponse:
    query_text = payload.get_query()
    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query content cannot be empty",
        )
    query_text = validate_and_sanitize_query(query_text)

    # 1. Verify session ownership
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    res = await session.execute(stmt)
    chat_session = res.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation session not found",
        )

    # 2. Save user message
    user_tokens = max(1, len(query_text.split()))
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=query_text,
        sources=None,
        token_count=user_tokens,
    )
    session.add(user_msg)
    await session.flush()

    # 3. Auto-title session if still named default
    if chat_session.title in ("New Consultation", "New Legal Chat", "New Chat", ""):
        words = query_text.strip().split()
        short_title = " ".join(words[:6])
        if len(short_title) > 42:
            short_title = short_title[:39] + "..."
        chat_session.title = short_title

    # 4. Execute search based on mode
    answer_text = ""
    sources_list: list[str] = []
    consumed_tokens = user_tokens + 250

    if payload.mode == "deep_search":
        if current_user.deep_search_credits <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have exhausted your 3 free Deep Search credits.",
            )
        research_req = LegalResearchRequest(query=query_text, max_precedents=3)
        research_res = perform_legal_research(research_req)
        synthesis_text = getattr(research_res, "synthesis", "") or getattr(research_res, "legal_analysis_and_strategy", "")
        answer_text = f"**JUDICIAL PRECEDENT & STRATEGY ANALYSIS**\n\n{synthesis_text}"
        for p in research_res.precedents:
            sources_list.append(f"🏛️ {p.case_title} [{p.citation or ''}] — {p.court or ''} ({p.year or ''})")
        
        current_user.deep_search_credits = max(0, current_user.deep_search_credits - 1)
        session.add(current_user)
        consumed_tokens += 500
    else:
        # Dual-stream RAG
        target_case_id = payload.case_id or chat_session.case_id
        rag_res = await generate_grounded_legal_answer(
            query=query_text,
            user_id=current_user.id,
            session=session,
            case_id=target_case_id,
            session_id=session_id,
        )
        answer_text = rag_res.get("answer", "")
        for s in rag_res.get("sources", []):
            title = s.get("document_title") or "Statutory Authority"
            page = s.get("page_number")
            sources_list.append(f"📖 {title}" + (f", Page {page}" if page else ""))
        consumed_tokens += max(100, len(answer_text.split()))

    # 5. Save assistant response
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer_text,
        sources=json.dumps(sources_list),
        token_count=consumed_tokens,
    )
    session.add(assistant_msg)

    chat_session.updated_at = datetime.now(timezone.utc)
    session.add(chat_session)
    await session.commit()
    await session.refresh(assistant_msg)

    return ChatMessageResponse(
        id=assistant_msg.id,
        session_id=assistant_msg.session_id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        sources=sources_list,
        token_count=assistant_msg.token_count,
        created_at=assistant_msg.created_at,
    )


@chat_router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a consultation session and all its messages",
)
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    res = await session.execute(stmt)
    chat_session = res.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation session not found",
        )

    # Delete all documents uploaded specifically to this consultation session
    doc_stmt = select(Document).where(
        Document.session_id == session_id,
        Document.user_id == current_user.id,
    )
    doc_res = await session.execute(doc_stmt)
    session_docs = doc_res.scalars().all()
    for doc in session_docs:
        try:
            if doc.file_path:
                Path(doc.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        await session.delete(doc)

    await session.delete(chat_session)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@chat_router.post(
    "/sessions/{session_id}/upload",
    response_model=ChatSessionDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document attached specifically to this consultation session",
)
async def upload_session_document(
    session_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionDocumentResponse:
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    res = await session.execute(stmt)
    chat_session = res.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation session not found",
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)

    ext = validate_upload(
        file_name=file.filename,
        content_type=file.content_type,
        file_size_bytes=file_size,
    )

    file_hash = compute_sha256(file_bytes)

    saved_path, _ = save_vault_file(
        user_id=current_user.id,
        file_bytes=file_bytes,
        extension=ext,
    )

    extracted_text = None
    processing_status = "uploaded"
    try:
        extracted_text, _ = extract_document_text(saved_path)
        processing_status = "extracted" if extracted_text else "uploaded"
    except Exception:
        processing_status = "extraction_failed"

    effective_title = file.filename or "Attached Document"

    new_doc = Document(
        user_id=current_user.id,
        session_id=session_id,
        title=effective_title,
        file_name=file.filename or "unknown",
        file_path=saved_path,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/octet-stream",
        file_hash=file_hash,
        document_type="chat_attachment",
        extracted_text=extracted_text,
        processing_status=processing_status,
    )

    session.add(new_doc)
    await session.commit()
    await session.refresh(new_doc)

    return ChatSessionDocumentResponse(
        id=new_doc.id,
        title=new_doc.title,
        file_name=new_doc.file_name,
        file_size_bytes=new_doc.file_size_bytes,
        created_at=new_doc.created_at,
    )
