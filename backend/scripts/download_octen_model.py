import sys
import time
from pathlib import Path
from huggingface_hub import snapshot_download

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models" / "octen-0.6b"

def download_octen():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Model Downloader] Target directory: {MODEL_DIR}")
    print("[Model Downloader] Connecting to Hugging Face Hub for 'Octen/Octen-Embedding-0.6B'...")

    t0 = time.time()
    try:
        downloaded_path = snapshot_download(
            repo_id="Octen/Octen-Embedding-0.6B",
            local_dir=str(MODEL_DIR),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        elapsed = time.time() - t0
        print(f"[Model Downloader] [OK] Download complete in {elapsed:.1f}s.")
        print(f"[Model Downloader] Weights stored at: {downloaded_path}")
        return True
    except Exception as exc:
        print(f"[Model Downloader] [ERROR] Failed to download model: {exc}")
        return False

if __name__ == "__main__":
    success = download_octen()
    sys.exit(0 if success else 1)
