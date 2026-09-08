import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from app.core.config import PROJECT_ROOT, get_settings

ALLOWED_EXTENSIONS: set[str] = {
    ".pdf",
    ".docx",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
}


ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
}

def get_vault_directory() -> Path:
    vault_dir = PROJECT_ROOT / "storage" / "vault"
    vault_dir.mkdir(parents=True,exist_ok=True)
    return vault_dir

def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_upload(
    file_name: str | None,
    content_type: str | None,
    file_size_bytes: int,
)-> str:
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    if not file_name or not file_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name cannot be empty"
        )

    if file_size_bytes <=0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)"
        )

    if file_size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB",
        )

    ext = Path(file_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {sorted(list(ALLOWED_EXTENSIONS))}",
        )

    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME content-type '{content_type}'",
        )
    
    return ext

def save_vault_file(
    user_id: int,
    file_bytes: bytes,
    extension: str,
) -> tuple[str, str]:
    
    vault_base = get_vault_directory()
    user_vault = vault_base / str(user_id)
    user_vault.mkdir(parents=True, exist_ok=True)
    
    unique_filename = f"{uuid4().hex}{extension}"
    target_path = user_vault / unique_filename
    
    target_path.write_bytes(file_bytes)

    file_hash = compute_sha256(file_bytes)
    return str(target_path.resolve()), file_hash