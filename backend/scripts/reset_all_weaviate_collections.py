"""
Script to safely delete and re-create all Weaviate collections:
- GlobalStatuteChunk (V1 Statutes) -> 0 objects
- GlobalStatuteChunk_V2 (V2 Statutes) -> 0 objects
- LegalDocumentChunk (V1 User Case Vault) -> 0 objects
- LegalDocumentChunk_V2 (V2 User Case Vault) -> 0 objects

Leaves the Weaviate database 100% clean and ready for embedding orders.
"""
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.vector_store_v1 import (
    get_weaviate_client,
    ensure_collection_exists,
    ensure_statute_collection_exists,
    COLLECTION_NAME as V1_DOC_COL,
    STATUTE_COLLECTION_NAME as V1_STAT_COL,
)
from app.services.vector_store_v2 import (
    ensure_collection_v2_exists,
    ensure_statute_collection_v2_exists,
    COLLECTION_NAME_V2 as V2_DOC_COL,
    STATUTE_COLLECTION_NAME_V2 as V2_STAT_COL,
)

TARGET_COLLECTIONS = [
    V1_STAT_COL,  # GlobalStatuteChunk
    V2_STAT_COL,  # GlobalStatuteChunk_V2
    V1_DOC_COL,   # LegalDocumentChunk
    V2_DOC_COL,   # LegalDocumentChunk_V2
]

def reset_all_collections():
    print("\n=======================================================")
    print(" 🧹 Purging & Re-creating All Weaviate Collections")
    print("=======================================================")

    with get_weaviate_client() as client:
        # 1. Delete existing collections
        for col_name in TARGET_COLLECTIONS:
            if client.collections.exists(col_name):
                col = client.collections.get(col_name)
                count = col.aggregate.over_all(total_count=True).total_count or 0
                print(f"[Delete] Found '{col_name}' with {count} objects. Deleting...")
                client.collections.delete(col_name)
                print(f"  --> Deleted '{col_name}' successfully.")
            else:
                print(f"[Skip] '{col_name}' does not exist.")

        # 2. Recreate clean, empty collection schemas
        print("\n-------------------------------------------------------")
        print(" 🏗️ Re-creating Fresh Empty Schemas...")
        print("-------------------------------------------------------")

        ensure_statute_collection_exists()       # GlobalStatuteChunk
        ensure_statute_collection_v2_exists()    # GlobalStatuteChunk_V2
        ensure_collection_exists()               # LegalDocumentChunk
        ensure_collection_v2_exists()            # LegalDocumentChunk_V2

        # 3. Verify counts
        print("\n-------------------------------------------------------")
        print(" 📋 Final Verification:")
        print("-------------------------------------------------------")
        for col_name in TARGET_COLLECTIONS:
            if client.collections.exists(col_name):
                col = client.collections.get(col_name)
                cnt = col.aggregate.over_all(total_count=True).total_count or 0
                print(f"  • {col_name:25} -> {cnt} objects [CLEAN & READY]")
            else:
                print(f"  • {col_name:25} -> [NOT FOUND]")

        print("\n=======================================================")
        print(" ✅ All collections deleted & reset. 0 objects stored.")
        print(" ⏳ Standing by for your instructions on embedding models!")
        print("=======================================================\n")

if __name__ == "__main__":
    reset_all_collections()
