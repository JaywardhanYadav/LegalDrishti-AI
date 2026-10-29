import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.core.security_guard import validate_and_sanitize_query
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatMessageResponse,
)
from app.services.retrieval_v2 import (
    generate_grounded_legal_answer_v2,
    stream_grounded_legal_answer_v2,
)

chat_router_v2 = APIRouter(prefix="/chat", tags=["V2 Chat (Fine-Tuned Local Retrieval)"])


@chat_router_v2.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    summary="Send legal prompt in session and receive synthesized answer via V2 local fine-tuned retrieval",
)
async def send_chat_message_v2(
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

    # 2. Record user message
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

    # 3. Execute V2 Retrieval + OpenAI GPT-4o synthesis
    target_case_id = payload.case_id or chat_session.case_id
    rag_res = await generate_grounded_legal_answer_v2(
        query=query_text,
        user_id=current_user.id,
        case_id=target_case_id,
        include_statutes=True,
    )
    answer_text = rag_res.get("answer", "")
    sources_raw = rag_res.get("sources", [])
    sources_formatted = []
    for s in sources_raw:
        title = s.get("document_title", "Statutory Provision")
        page = s.get("page_number")
        sources_formatted.append(f"⚖️ {title}" + (f", Page {page}" if page else ""))

    consumed_tokens = user_tokens + max(100, len(answer_text.split()))

    # 4. Save assistant response
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer_text,
        sources=json.dumps(sources_formatted),
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
        sources=sources_formatted,
        token_count=assistant_msg.token_count,
        created_at=assistant_msg.created_at,
    )


@chat_router_v2.post(
    "/sessions/{session_id}/messages/stream",
    summary="Send legal prompt and stream synthesized answer word-by-word (SSE) using V2 local retrieval",
)
async def stream_chat_message_v2(
    session_id: int,
    payload: ChatMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
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

    # 2. Save user message immediately
    user_tokens = max(1, len(query_text.split()))
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=query_text,
        sources=None,
        token_count=user_tokens,
    )
    session.add(user_msg)
    chat_session.updated_at = datetime.now(timezone.utc)
    session.add(chat_session)
    await session.commit()

    target_case_id = payload.case_id or chat_session.case_id
    user_id = current_user.id

    async def sse_event_stream():
        try:
            formatted_sources = []
            async for event in stream_grounded_legal_answer_v2(
                query=query_text,
                user_id=user_id,
                case_id=target_case_id,
                include_statutes=True,
            ):
                if event["type"] == "sources":
                    for s in event.get("sources", []):
                        title = s.get("document_title") or "Indian Bare Act"
                        page = s.get("page_number")
                        formatted_sources.append(f"⚖️ {title}" + (f", Page {page}" if page else ""))
                    yield f"data: {json.dumps({'type': 'sources', 'sources': formatted_sources})}\n\n"

                elif event["type"] == "content":
                    yield f"data: {json.dumps({'type': 'content', 'delta': event['delta']})}\n\n"

                elif event["type"] == "done":
                    full_ans = event.get("full_answer", "")
                    asst_msg = ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=full_ans,
                        sources=json.dumps(formatted_sources),
                        token_count=user_tokens + max(50, len(full_ans.split())),
                    )
                    session.add(asst_msg)
                    await session.commit()
                    yield f"data: {json.dumps({'type': 'done', 'full_answer': full_ans, 'sources': formatted_sources})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
