from transformers import AutoTokenizer, T5ForConditionalGeneration
import torch
from app.core.vector_store import VectorStore
from app.models.query import QueryResponse
from typing import List, Dict
import os
import logging
import gc

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self):
        self.vector_store = VectorStore()
        self.model_name = "google/flan-t5-base"  # Changed to public model
        self.device = os.getenv("MODEL_DEVICE", "cpu")
        self.max_input_tokens = 4096
        self._load_model()

    def _load_model(self):
        """Load model with proper memory management"""
        try:
            logger.info(f"Initializing RAG engine with device: {self.device}")
            
            # Clear any existing tensors
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                low_cpu_mem_usage=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to("cpu")
                
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    async def process_query(self, question: str, document_id: str, context_window: int = 4096) -> QueryResponse:
        try:
            # Update max input tokens based on context window
            self.max_input_tokens = min(context_window, 4096)  # Cap at model's limit
            
            # Retrieve relevant chunks
            relevant_chunks = await self.vector_store.search(document_id, question, k=5)  # Get more chunks initially
            
            # Prepare context within token limit
            context_texts = []
            total_tokens = 0
            prompt_template = """
Given the following context, please answer the question. Use only the information provided in the context.
If you cannot find the answer in the context, say "I cannot find the answer in the provided context."

Context:
{context}

Question: {question}

Answer:"""
            
            # Calculate tokens for prompt template
            template_tokens = len(self.tokenizer.encode(prompt_template.format(context="", question=question)))
            available_tokens = self.max_input_tokens - template_tokens - 100  # Reserve tokens for the answer
            
            # Add chunks while respecting token limit
            for chunk in relevant_chunks:
                chunk_tokens = len(self.tokenizer.encode(chunk.text))
                if total_tokens + chunk_tokens > available_tokens:
                    break
                context_texts.append(chunk.text)
                total_tokens += chunk_tokens
            
            context = "\n".join(context_texts)
            
            # Create prompt
            prompt = prompt_template.format(context=context, question=question)

            try:
                # Generate response
                # T5 expects a more straightforward input format
                inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_input_tokens).to(self.device)
                
                with torch.inference_mode():
                    outputs = self.model.generate(
                        **inputs,
                        max_length=512,  # T5 doesn't need the input length added here
                        temperature=0.7,
                        top_p=0.95,
                        do_sample=True,
                        num_beams=4,  # Adding beam search for better quality
                        early_stopping=True
                    )
                
                answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Clean up GPU memory if using CUDA
                if self.device == "cuda":
                    del inputs, outputs
                    torch.cuda.empty_cache()
                
            except RuntimeError as e:
                if "out of memory" in str(e):
                    # If we run out of memory, try to recover
                    if self.device == "cuda":
                        torch.cuda.empty_cache()
                        gc.collect()
                    self._load_model()  # Reload model
                    raise RuntimeError("Insufficient GPU memory. Please try with a smaller context window.")
                raise
            
            # Remove the prompt from the answer
            answer = answer.split("Answer:")[-1].strip()
            
            # Calculate confidence based on context coverage and similarity scores
            avg_similarity = sum(
                chunk.metadata.get('similarity_score', 0) 
                for chunk in relevant_chunks[:len(context_texts)]
            ) / len(context_texts) if context_texts else 0
            
            confidence = min(1.0, (len(context_texts) / 5) * (1 - avg_similarity/2))
            
            return QueryResponse(
                answer=answer,
                context=context_texts,
                confidence=confidence,
                metadata={
                    "model": self.model_name,
                    "chunks_used": len(context_texts),
                    "total_tokens": total_tokens,
                    "context_window": self.max_input_tokens,
                    "device": self.device,
                    "avg_similarity_score": float(avg_similarity)
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            # Ensure memory is cleaned up on error
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
            raise