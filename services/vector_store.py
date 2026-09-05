"""
Vision AI v2.0 - Vector Store Service
======================================
Semantic search and vector database for RAG.
Uses ChromaDB (lightweight, in‑memory, persistent) and BGE‑large‑en‑v1.5.
BGE models consistently outperform OpenAI's text-embedding-3-small in RAG tasks.

Features:
- Document chunking (by tokens or characters)
- Embedding generation with BGE‑large‑en‑v1.5 (SOTA, 1024‑dim)
- Persistent vector storage with ChromaDB
- Semantic retrieval (top‑K relevant chunks)
- Automatic cleanup and deduplication
"""

import os
import hashlib
import shutil
import asyncio
import functools
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

# ==========================================================
# LOGGING SETUP
# ==========================================================
logger = logging.getLogger("vision-ai.vectorstore")

# ==========================================================
# CONFIGURATION
# ==========================================================

# 🚀 UPGRADED: Best open‑source embedding model for RAG (1024 dims)
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"

# Improved chunking for higher precision
CHUNK_SIZE = 500          # Characters per chunk (smaller = more precise)
CHUNK_OVERLAP = 100        # Overlap between chunks (for continuity)

DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"  # Persistent storage path
COLLECTION_NAME = "vision_ai_docs"
MAX_RETRIES = 3            # Retry count for ChromaDB operations
CACHE_SIZE = 1000          # Max entries in embedding cache

# ==========================================================
# EXCEPTIONS
# ==========================================================
class VectorStoreError(Exception):
    """Base exception for vector store errors."""
    pass

class EmbeddingError(VectorStoreError):
    """Raised when embedding generation fails."""
    pass

class ChromaDBError(VectorStoreError):
    """Raised when ChromaDB operations fail."""
    pass

# ==========================================================
# EMBEDDING ENGINE (BGE-Large-en-v1.5)
# ==========================================================
class LocalEmbeddingFunction:
    """Wrapper for sentence-transformers to work with ChromaDB."""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None  # Lazy load the model
        self._embedding_cache = {}  # Cache for frequently used texts
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        # Load the model only once on the first call
        if self._model is None:
            logger.info(f"⏳ Loading embedding model {self.model_name}...")
            start = time.time()
            try:
                # BGE models expect normalize_embeddings=True at encode time for cosine similarity
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"✅ Embedding model loaded in {time.time() - start:.1f}s (1024 dims)")
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model: {e}")
                raise EmbeddingError(f"Failed to load embedding model: {e}")
        
        # Check cache for single texts
        if len(texts) == 1 and texts[0] in self._embedding_cache:
            return [self._embedding_cache[texts[0]]]
        
        # Compute embeddings (normalize for cosine similarity with BGE)
        try:
            embeddings = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).tolist()
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")
        
        # Cache for future use (limit cache size)
        for text, emb in zip(texts, embeddings):
            if len(self._embedding_cache) < CACHE_SIZE:
                self._embedding_cache[text] = emb
        
        return embeddings

# Singleton embedding function
embedding_func = LocalEmbeddingFunction()

# ==========================================================
# UTILITY FUNCTIONS
# ==========================================================
def run_sync_in_thread(func, *args, **kwargs):
    """Run a synchronous function in a thread to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

def generate_doc_id(text: str) -> str:
    """Generate a unique document ID from text content."""
    return hashlib.md5(text[:2000].encode('utf-8')).hexdigest()

def generate_chunk_id(doc_id: str, index: int) -> str:
    """Generate a unique chunk ID."""
    return f"{doc_id}_{index}"

# ==========================================================
# CHROMA DB CLIENT
# ==========================================================
class VectorStore:
    """Main vector store manager for RAG."""

    def __init__(self, persist_directory: Path = DB_PATH):
        self.persist_directory = persist_directory
        
        try:
            self.persist_directory.mkdir(exist_ok=True, parents=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    persist_directory=str(self.persist_directory)
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_func,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"✅ Vector store initialized at {persist_directory}")
            logger.info(f"   Collection: {COLLECTION_NAME}, Chunks: {self.count()}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize vector store: {e}")
            raise ChromaDBError(f"Vector store initialization failed: {e}")

    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
        """Split text into overlapping chunks with intelligent boundaries."""
        if not text or not text.strip():
            return []
            
        if len(text) <= chunk_size:
            return [text.strip()]
        
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence/paragraph boundary
            if end < len(text):
                # Look for period, newline, or space within last 100 chars
                boundary = text.rfind(". ", start + chunk_size - 100, end)
                if boundary == -1:
                    boundary = text.rfind("\n", start + chunk_size - 100, end)
                if boundary == -1:
                    boundary = text.rfind(" ", start + chunk_size - 100, end)
                if boundary != -1:
                    end = boundary + 1
                    
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap
            if start < 0:
                start = 0
                
        return chunks

    def _normalize_metadata(self, metadata: Dict) -> Dict:
        """Ensure all metadata keys are strings (ChromaDB requirement)."""
        if not metadata:
            return {}
        
        safe_metadata = {}
        for k, v in metadata.items():
            safe_key = str(k)
            # Convert non-string values to strings
            if isinstance(v, (dict, list)):
                safe_value = str(v)
            elif v is None:
                safe_value = ""
            else:
                safe_value = v
            safe_metadata[safe_key] = safe_value
            
        return safe_metadata

    async def add_document_async(self, text: str, metadata: Dict = None) -> List[str]:
        """Async version of add_document."""
        return await run_sync_in_thread(self.add_document, text, metadata)

    def add_document(self, text: str, metadata: Dict = None) -> List[str]:
        """
        Add a document to the vector store.
        
        Args:
            text: Full document text
            metadata: Optional metadata (filename, user, timestamp, etc.)
            
        Returns:
            List of chunk IDs
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to add_document")
            return []
        
        # Normalize metadata
        safe_metadata = self._normalize_metadata(metadata)
        
        # Generate a unique document ID
        doc_id = generate_doc_id(text)
        
        # Check if document already exists
        if safe_metadata.get("filename"):
            try:
                existing = self.collection.get(where={"filename": safe_metadata["filename"]})
                if existing and existing.get("ids") and len(existing["ids"]) > 0:
                    logger.debug(f"Document {safe_metadata['filename']} already exists, skipping")
                    return existing["ids"]
            except Exception as e:
                logger.debug(f"Document existence check failed: {e}")

        # Chunk the text
        chunks = self._chunk_text(text)
        if not chunks:
            logger.warning(f"No chunks generated for document {doc_id}")
            return []
        
        # Generate IDs for each chunk
        chunk_ids = [generate_chunk_id(doc_id, i) for i in range(len(chunks))]
        
        # Prepare metadata for each chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            m = {
                "chunk_index": i,
                "total_chunks": len(chunks),
                "doc_id": doc_id,
                "chunk_length": len(chunk),
                "upload_time": time.time(),
                **safe_metadata
            }
            metadatas.append(m)
        
        # Add to ChromaDB with retry logic
        for attempt in range(MAX_RETRIES):
            try:
                self.collection.add(
                    ids=chunk_ids,
                    documents=chunks,
                    metadatas=metadatas
                )
                logger.debug(f"Added {len(chunks)} chunks for document {doc_id}")
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"❌ Failed to add document {doc_id} after {MAX_RETRIES} attempts: {e}")
                    raise ChromaDBError(f"Failed to add document: {e}")
                logger.warning(f"⚠️ ChromaDB add failed (attempt {attempt+1}), retrying...")
                time.sleep(1)
        
        return chunk_ids

    async def search_async(self, query: str, top_k: int = 5, filter_metadata: Dict = None) -> List[Dict]:
        """Async version of search."""
        return await run_sync_in_thread(self.search, query, top_k, filter_metadata)

    def search(self, query: str, top_k: int = 8, filter_metadata: Dict = None, min_score: float = 0.25) -> List[Dict]:
        """
        Search for relevant document chunks.
        
        Args:
            query: User query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"filename": "doc.pdf"})
            
        Returns:
            List of dicts with text, metadata, and relevance score
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to search")
            return []
        
        # Normalize filter metadata
        safe_filter = self._normalize_metadata(filter_metadata) if filter_metadata else None
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=safe_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"⚠️ ChromaDB query failed: {e}")
            raise ChromaDBError(f"Search failed: {e}")
        
        # Format results
        formatted = []
        if results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                # Convert distance to similarity (1 - distance for cosine)
                similarity = 1 - results["distances"][0][i] if results.get("distances") else 0.5
                if similarity < min_score:
                    continue
                formatted.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": round(similarity, 4),
                    "id": results["ids"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0,
                    "relevance": f"{similarity * 100:.1f}%"
                })
        
        logger.debug(f"Search returned {len(formatted)} results for query: {query[:50]}...")
        return formatted

    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks for a document."""
        try:
            self.collection.delete(where={"doc_id": doc_id})
            logger.debug(f"Deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"⚠️ Failed to delete document {doc_id}: {e}")
            return False

    def delete_by_filename(self, filename: str) -> bool:
        """Delete all chunks for a specific filename."""
        try:
            self.collection.delete(where={"filename": filename})
            logger.debug(f"Deleted filename {filename}")
            return True
        except Exception as e:
            logger.error(f"⚠️ Failed to delete filename {filename}: {e}")
            return False

    def clear_all(self):
        """Clear all documents from the vector store."""
        try:
            self.collection.delete(where={})
            logger.info("🧹 Vector store cleared")
        except Exception as e:
            logger.error(f"⚠️ Failed to clear vector store: {e}")
            raise ChromaDBError(f"Failed to clear vector store: {e}")

    def count(self) -> int:
        """Get number of chunks in the store."""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"⚠️ Failed to get count: {e}")
            return 0

    def get_document_chunks(self, doc_id: str) -> List[str]:
        """Retrieve all chunk texts for a document."""
        try:
            results = self.collection.get(where={"doc_id": doc_id})
            return results.get("documents", []) if results else []
        except Exception as e:
            logger.error(f"⚠️ Failed to get document chunks: {e}")
            return []

    def get_documents_metadata(self) -> List[Dict]:
        """Get unique document metadata (without chunks)."""
        try:
            results = self.collection.get(include=["metadatas"])
            if not results or not results.get("metadatas"):
                return []
            
            seen_docs = set()
            unique_metadata = []
            for m in results["metadatas"]:
                doc_id = m.get("doc_id")
                if doc_id and doc_id not in seen_docs:
                    seen_docs.add(doc_id)
                    unique_metadata.append(m)
            return unique_metadata
        except Exception as e:
            logger.error(f"⚠️ Failed to get documents metadata: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get vector store statistics for monitoring."""
        return {
            "total_chunks": self.count(),
            "unique_documents": len(self.get_documents_metadata()),
            "collection_name": COLLECTION_NAME,
            "persist_directory": str(self.persist_directory),
            "embedding_model": EMBEDDING_MODEL,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "cache_size": len(embedding_func._embedding_cache) if embedding_func else 0,
        }

# ==========================================================
# SINGLETON INSTANCE
# ==========================================================
# Global vector store instance
try:
    vector_store = VectorStore()
except Exception as e:
    logger.error(f"❌ Failed to initialize vector store: {e}")
    vector_store = None

# ==========================================================
# EXPORTS
# ==========================================================
__all__ = [
    "vector_store",
    "VectorStore",
    "VectorStoreError",
    "EmbeddingError",
    "ChromaDBError",
]

logger.info("👁️ Vision AI Vector Store Service v2.0 - Ready")