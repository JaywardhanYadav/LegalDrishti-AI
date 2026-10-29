"""
Hybrid Experiment Package (Testing Track)
=========================================
Houses experimental pipelines for research and evaluation:
1. Recursive_FineTune_Model:
   - Chunking: V1 Docling + LangChain Recursive Character Splitter
   - Embedding: V2 Fine-Tuned Octen-0.6B (1024-D)
2. Recursive_Base_Octen:
   - Chunking: V1 Docling + LangChain Recursive Character Splitter
   - Embedding: Base (Non-Fine-Tuned) Octen-0.6B (1024-D)
"""
from app.services.hybrid_experiment.vector_store_recursive_finetune import (
    ensure_recursive_finetune_collection_exists,
    hybrid_search_recursive_finetune,
    RECURSIVE_FINETUNE_COLLECTION_NAME,
)
from app.services.hybrid_experiment.retrieval_recursive_finetune import (
    retrieve_statutory_context_recursive_finetune,
    generate_grounded_legal_answer_recursive_finetune,
)
from app.services.hybrid_experiment.embeddings_base_octen import (
    get_embedding_base_octen,
    get_embeddings_batch_base_octen,
)
from app.services.hybrid_experiment.vector_store_recursive_base_octen import (
    ensure_recursive_base_octen_collection_exists,
    hybrid_search_recursive_base_octen,
    RECURSIVE_BASE_OCTEN_COLLECTION_NAME,
)
from app.services.hybrid_experiment.retrieval_recursive_base_octen import (
    retrieve_statutory_context_recursive_base_octen,
    generate_grounded_legal_answer_recursive_base_octen,
)

__all__ = [
    # Recursive + Fine-Tuned
    "ensure_recursive_finetune_collection_exists",
    "hybrid_search_recursive_finetune",
    "RECURSIVE_FINETUNE_COLLECTION_NAME",
    "retrieve_statutory_context_recursive_finetune",
    "generate_grounded_legal_answer_recursive_finetune",
    # Recursive + Base Octen (Non-Fine-Tuned)
    "get_embedding_base_octen",
    "get_embeddings_batch_base_octen",
    "ensure_recursive_base_octen_collection_exists",
    "hybrid_search_recursive_base_octen",
    "RECURSIVE_BASE_OCTEN_COLLECTION_NAME",
    "retrieve_statutory_context_recursive_base_octen",
    "generate_grounded_legal_answer_recursive_base_octen",
]
