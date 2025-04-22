import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Callable
import pickle
from pathlib import Path
import logging
from app.models.document import DocumentChunk
import asyncio
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.index_dir = Path("vector_indices")
        self.index_dir.mkdir(exist_ok=True)
        self.dimension = 384  # Model embedding dimension
        self._executor = ThreadPoolExecutor(max_workers=1)
        
    async def add_chunks(self, document_id: str, chunks: List[DocumentChunk], progress_callback: Optional[Callable[[str, float], None]] = None) -> None:
        if not chunks:
            raise ValueError("No chunks provided for indexing")
            
        try:
            # Update progress
            if progress_callback:
                await progress_callback("Preparing chunks for indexing...", 0.1)
                
            texts = [chunk.text for chunk in chunks]
            total_chunks = len(texts)
            
            # Encode chunks in batches to show progress
            batch_size = 32
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                # Run encoding in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    self._executor,
                    lambda: self.model.encode(batch, show_progress_bar=False)
                )
                all_embeddings.append(embeddings)
                
                if progress_callback:
                    progress = 0.1 + 0.6 * (min(i + batch_size, total_chunks) / total_chunks)
                    await progress_callback(
                        f"Encoding chunks ({min(i + batch_size, total_chunks)}/{total_chunks})...",
                        progress
                    )
            
            embeddings = np.vstack(all_embeddings)
            
            if len(embeddings) != len(chunks):
                raise ValueError(f"Mismatch between embeddings ({len(embeddings)}) and chunks ({len(chunks)})")
            
            if progress_callback:
                await progress_callback("Creating FAISS index...", 0.8)
            
            # Create FAISS index
            index = faiss.IndexFlatL2(self.dimension)
            index.add(np.array(embeddings).astype('float32'))
            
            if progress_callback:
                await progress_callback("Saving index and metadata...", 0.9)
            
            # Save index and metadata
            index_path = self.index_dir / f"{document_id}.index"
            chunks_path = self.index_dir / f"{document_id}.pkl"
            
            faiss.write_index(index, str(index_path))
            with open(chunks_path, 'wb') as f:
                pickle.dump(chunks, f)
                
            if progress_callback:
                await progress_callback("Indexing completed", 1.0)
                
            logger.info(f"Successfully indexed {len(chunks)} chunks for document {document_id}")
            
        except Exception as e:
            logger.error(f"Error indexing chunks for document {document_id}: {str(e)}")
            # Clean up any partially created files
            self._cleanup_index_files(document_id)
            raise
            
    async def search(self, document_id: str, query: str, k: int = 3) -> List[DocumentChunk]:
        try:
            # Validate inputs
            if not query.strip():
                raise ValueError("Empty query provided")
            if k < 1:
                raise ValueError("k must be positive")
                
            index_path = self.index_dir / f"{document_id}.index"
            chunks_path = self.index_dir / f"{document_id}.pkl"
            
            if not index_path.exists() or not chunks_path.exists():
                raise FileNotFoundError(f"No index found for document {document_id}")
            
            # Load index and metadata
            index = faiss.read_index(str(index_path))
            with open(chunks_path, 'rb') as f:
                chunks = pickle.load(f)
            
            # Run query encoding in thread pool
            loop = asyncio.get_event_loop()
            query_vector = await loop.run_in_executor(
                self._executor,
                lambda: self.model.encode([query])
            )
            
            # Search similar vectors
            D, I = index.search(np.array(query_vector).astype('float32'), min(k, len(chunks)))
            
            # Return relevant chunks sorted by similarity
            results = []
            for score, idx in zip(D[0], I[0]):
                if idx < len(chunks):  # Safety check
                    chunk = chunks[idx]
                    # Add similarity score to metadata
                    chunk.metadata['similarity_score'] = float(score)
                    results.append(chunk)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error searching document {document_id}: {str(e)}")
            raise
            
    def _cleanup_index_files(self, document_id: str) -> None:
        """Clean up index files in case of errors"""
        try:
            index_path = self.index_dir / f"{document_id}.index"
            chunks_path = self.index_dir / f"{document_id}.pkl"
            
            if index_path.exists():
                index_path.unlink()
            if chunks_path.exists():
                chunks_path.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up index files: {str(e)}")
            
    async def delete_document(self, document_id: str) -> bool:
        """Delete document indices"""
        try:
            self._cleanup_index_files(document_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False