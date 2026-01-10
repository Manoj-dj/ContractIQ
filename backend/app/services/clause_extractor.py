import torch
import torch.quantization
import numpy as np
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from typing import List, Dict, Tuple
from collections import defaultdict
from app.config import settings
from app.core.logger import get_logger
import time

logger = get_logger(__name__)


class ClauseExtractor:
    """
    OPTIMIZED Contract clause extraction service using fine-tuned TinyRoBERTa model
    
    Optimizations:
    - INT8 Dynamic Quantization: 2-3x faster inference, 4x smaller model
    - Batch Inference: Process multiple chunks simultaneously
    - Expected speedup: 12 min → 3-4 min (3-4x faster)
    """
    
    def __init__(self):
        self.model_path = settings.MODEL_PATH
        self.device = settings.DEVICE
        self.max_length = settings.MAX_LENGTH
        self.stride = settings.STRIDE
        self.null_threshold = settings.NULL_THRESHOLD
        self.n_best = settings.N_BEST
        self.max_answer_length = settings.MAX_ANSWER_LENGTH
        
        # Batch inference configuration
        self.batch_size = self._determine_optimal_batch_size()
        
        logger.info(f"Initializing OPTIMIZED ClauseExtractor with model: {self.model_path}")
        logger.info(f"Optimizations: INT8 Quantization + Batch Inference (batch_size={self.batch_size})")
        
        # Load and optimize model
        self._load_model()
    
    def _determine_optimal_batch_size(self) -> int:
        """
        Determine optimal batch size based on device
        
        Returns:
            Optimal batch size for inference
        """
        if self.device == "cuda":
            return 16  # GPU can handle larger batches
        else:
            return 8   # CPU optimal batch size
    
    def _load_model(self):
        """Load model, tokenizer, and apply INT8 quantization"""
        try:
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            
            # Load base model
            logger.info("Loading base model...")
            model = AutoModelForQuestionAnswering.from_pretrained(self.model_path)
            
            # Force CPU for quantization (quantization works best on CPU)
            if self.device == "cuda":
                logger.warning("INT8 quantization requires CPU. Using CPU for optimized inference.")
                self.device = "cpu"
            
            model.to("cpu")
            model.eval()
            
            # Apply INT8 Dynamic Quantization
            logger.info("Applying INT8 dynamic quantization (this may take 10-20 seconds)...")
            quantization_start = time.time()
            
            self.model = torch.quantization.quantize_dynamic(
                model,
                {torch.nn.Linear},  # Quantize all Linear layers
                dtype=torch.qint8    # Use INT8 quantization
            )
            
            quantization_time = time.time() - quantization_start
            
            # Calculate model size reduction
            original_size = sum(p.numel() * p.element_size() for p in model.parameters()) / (1024 * 1024)
            quantized_size = sum(p.numel() * p.element_size() for p in self.model.parameters()) / (1024 * 1024)
            size_reduction = ((original_size - quantized_size) / original_size * 100)
            
            logger.info(f"✅ INT8 quantization completed in {quantization_time:.2f}s")
            logger.info(f"✅ Model size: {original_size:.2f}MB → {quantized_size:.2f}MB (reduced by {size_reduction:.1f}%)")
            logger.info(f"✅ Model loaded successfully on device: {self.device}")
        
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}", exc_info=True)
            raise
    
    def extract_all_clauses(self, contract_text: str, char_to_page_map: dict = None) -> Dict[str, Dict]:
        """
        Extract all 41 CUAD clause types from contract using OPTIMIZED batch inference
        
        Args:
            contract_text: Full contract text
            char_to_page_map: Optional mapping of character positions to page numbers
        
        Returns:
            Dictionary mapping clause_type to extraction results
        """
        logger.info(f"🚀 Starting OPTIMIZED extraction of {len(settings.CUAD_QUESTIONS)} clause types")
        extraction_start_time = time.time()
        
        results = {}
        
        # OPTIMIZATION: Batch process all questions
        all_question_results = self._batch_process_all_questions(
            settings.CUAD_QUESTIONS,
            contract_text,
            char_to_page_map
        )
        
        # Format results
        for question, answers in zip(settings.CUAD_QUESTIONS, all_question_results):
            clause_type = self._extract_clause_type(question)
            
            if answers:
                # Take best answer
                best_answer = answers[0]
                results[clause_type] = {
                    "extracted_text": best_answer["text"],
                    "confidence": best_answer["confidence"],
                    "found": True,
                    "page_number": best_answer.get("page_number"),
                    "char_start": best_answer.get("char_start"),
                    "char_end": best_answer.get("char_end"),
                    "all_answers": answers
                }
            else:
                results[clause_type] = {
                    "extracted_text": None,
                    "confidence": 0.0,
                    "found": False,
                    "page_number": None,
                    "char_start": None,
                    "char_end": None,
                    "all_answers": []
                }
        
        total_time = time.time() - extraction_start_time
        found_count = sum(1 for r in results.values() if r['found'])
        
        logger.info(f"✅ Extraction complete in {total_time:.2f}s ({total_time/60:.2f} minutes)")
        logger.info(f"✅ Found {found_count}/{len(settings.CUAD_QUESTIONS)} clauses")
        logger.info(f"✅ Average time per clause: {total_time / len(settings.CUAD_QUESTIONS):.2f}s")
        
        return results
    
    def _batch_process_all_questions(
        self,
        questions: List[str],
        context: str,
        char_to_page_map: dict = None
    ) -> List[List[Dict]]:
        """
        Process all questions using batch inference for maximum efficiency
        
        Args:
            questions: List of all question strings
            context: Contract text
            char_to_page_map: Optional character-to-page mapping
        
        Returns:
            List of answer lists (one per question)
        """
        logger.info(f"📦 Batch processing {len(questions)} questions")
        
        # Step 1: Tokenize all questions and prepare chunks
        all_chunks_data = []
        
        for q_idx, question in enumerate(questions):
            # Tokenize with chunking
            inputs = self.tokenizer(
                question,
                context,
                max_length=self.max_length,
                stride=self.stride,
                truncation="only_second",
                return_overflowing_tokens=True,
                return_offsets_mapping=True,
                padding="max_length",
                return_tensors="pt"
            )
            
            # Store all chunks for this question
            num_chunks = len(inputs["input_ids"])
            
            for i in range(num_chunks):
                all_chunks_data.append({
                    "question_idx": q_idx,
                    "chunk_idx": i,
                    "input_ids": inputs["input_ids"][i],
                    "attention_mask": inputs["attention_mask"][i],
                    "offset_mapping": inputs["offset_mapping"][i],
                    "sequence_ids": inputs.sequence_ids(i)
                })
        
        total_chunks = len(all_chunks_data)
        logger.info(f"📊 Total chunks to process: {total_chunks}")
        logger.info(f"📊 Processing in batches of {self.batch_size}")
        
        # Step 2: Batch process all chunks
        all_chunk_results = self._batch_inference(all_chunks_data, context, char_to_page_map)
        
        # Step 3: Aggregate results per question
        question_results = [[] for _ in questions]
        
        for chunk_result in all_chunk_results:
            q_idx = chunk_result["question_idx"]
            question_results[q_idx].extend(chunk_result["answers"])
        
        # Step 4: Deduplicate and sort answers for each question
        final_results = []
        for answers in question_results:
            aggregated = self._aggregate_answers(answers)
            final_results.append(aggregated)
        
        return final_results
    
    def _batch_inference(
        self,
        chunks_data: List[Dict],
        context: str,
        char_to_page_map: dict = None
    ) -> List[Dict]:
        """
        Process chunks in batches using vectorized inference
        
        Args:
            chunks_data: List of chunk dictionaries
            context: Contract text
            char_to_page_map: Character to page mapping
        
        Returns:
            List of results per chunk
        """
        all_results = []
        num_chunks = len(chunks_data)
        num_batches = (num_chunks + self.batch_size - 1) // self.batch_size
        
        batch_start_time = time.time()
        
        # Process in batches
        for batch_idx in range(0, num_chunks, self.batch_size):
            batch_end = min(batch_idx + self.batch_size, num_chunks)
            batch = chunks_data[batch_idx:batch_end]
            current_batch_num = batch_idx // self.batch_size + 1
            
            if current_batch_num % 10 == 1:  # Log every 10th batch
                logger.debug(f"Processing batch {current_batch_num}/{num_batches}")
            
            # Stack batch inputs
            input_ids = torch.stack([chunk["input_ids"] for chunk in batch]).to(self.device)
            attention_mask = torch.stack([chunk["attention_mask"] for chunk in batch]).to(self.device)
            
            # Batch inference (OPTIMIZED)
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            
            # Process each item in batch
            for i, chunk in enumerate(batch):
                start_logits = outputs.start_logits[i].cpu().numpy()
                end_logits = outputs.end_logits[i].cpu().numpy()
                
                # Extract answers from this chunk
                answers = self._extract_answers_from_chunk(
                    start_logits,
                    end_logits,
                    chunk["offset_mapping"],
                    chunk["sequence_ids"],
                    context,
                    char_to_page_map
                )
                
                all_results.append({
                    "question_idx": chunk["question_idx"],
                    "chunk_idx": chunk["chunk_idx"],
                    "answers": answers
                })
        
        batch_total_time = time.time() - batch_start_time
        logger.info(f"⚡ Batch inference completed in {batch_total_time:.2f}s")
        logger.info(f"⚡ Processed {num_chunks} chunks in {num_batches} batches")
        logger.info(f"⚡ Average time per batch: {batch_total_time / num_batches:.2f}s")
        
        return all_results
    
    def _extract_answers_from_chunk(
        self,
        start_logits: np.ndarray,
        end_logits: np.ndarray,
        offset_mapping,
        sequence_ids,
        context: str,
        char_to_page_map: dict = None
    ) -> List[Dict]:
        """
        Extract answer spans from a single chunk's logits
        
        Args:
            start_logits: Start position logits
            end_logits: End position logits
            offset_mapping: Token offset mapping
            sequence_ids: Sequence IDs (0=question, 1=context)
            context: Full contract text
            char_to_page_map: Character to page mapping
        
        Returns:
            List of answer dictionaries
        """
        answers = []
        
        # Calculate null score (CLS token)
        null_score = start_logits[0] + end_logits[0]
        
        # Mask non-context tokens
        for idx, s_id in enumerate(sequence_ids):
            if s_id != 1:  # Not part of context
                start_logits[idx] = -10000
                end_logits[idx] = -10000
        
        # Get top candidate spans
        start_indexes = np.argsort(start_logits)[-self.n_best:][::-1]
        end_indexes = np.argsort(end_logits)[-self.n_best:][::-1]
        
        for start_idx in start_indexes:
            for end_idx in end_indexes:
                # Validate span
                if end_idx < start_idx:
                    continue
                
                if offset_mapping[start_idx] is None or offset_mapping[end_idx] is None:
                    continue
                
                length = end_idx - start_idx + 1
                if length > self.max_answer_length:
                    continue
                
                # Extract span
                start_char = int(offset_mapping[start_idx][0])
                end_char = int(offset_mapping[end_idx][1])
                text = context[start_char:end_char].strip()
                
                if not text or len(text) < 5:
                    continue
                
                # Calculate score
                span_score = start_logits[start_idx] + end_logits[end_idx]
                confidence_delta = span_score - null_score
                
                # Only keep if confidence exceeds threshold
                if confidence_delta > self.null_threshold:
                    # Determine page number if mapping provided
                    page_number = None
                    if char_to_page_map:
                        page_number = char_to_page_map.get(start_char)
                    
                    answers.append({
                        "text": text,
                        "score": float(span_score),
                        "confidence": float(self._sigmoid(confidence_delta)),
                        "char_start": start_char,
                        "char_end": end_char,
                        "page_number": page_number
                    })
        
        return answers
    
    def _answer_question(self, question: str, context: str, char_to_page_map: dict = None) -> List[Dict]:
        """
        Answer a single question using the model with chunking and aggregation
        (Kept for backwards compatibility, but not used in optimized flow)
        
        Args:
            question: Question string
            context: Contract text
            char_to_page_map: Optional character-to-page mapping
        
        Returns:
            List of answer dictionaries sorted by confidence
        """
        try:
            # Tokenize with chunking
            inputs = self.tokenizer(
                question,
                context,
                max_length=self.max_length,
                stride=self.stride,
                truncation="only_second",
                return_overflowing_tokens=True,
                return_offsets_mapping=True,
                padding="max_length",
                return_tensors="pt"
            )
            
            all_answers = []
            
            # Process each chunk
            for i in range(len(inputs["input_ids"])):
                input_ids = inputs["input_ids"][i].unsqueeze(0).to(self.device)
                attention_mask = inputs["attention_mask"][i].unsqueeze(0).to(self.device)
                offsets = inputs["offset_mapping"][i]
                sequence_ids = inputs.sequence_ids(i)
                
                # Model inference
                with torch.no_grad():
                    outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                
                start_logits = outputs.start_logits[0].cpu().numpy()
                end_logits = outputs.end_logits[0].cpu().numpy()
                
                # Extract answers
                answers = self._extract_answers_from_chunk(
                    start_logits,
                    end_logits,
                    offsets,
                    sequence_ids,
                    context,
                    char_to_page_map
                )
                
                all_answers.extend(answers)
            
            # Deduplicate and aggregate answers
            aggregated_answers = self._aggregate_answers(all_answers)
            
            return aggregated_answers
        
        except Exception as e:
            logger.error(f"Error during question answering: {str(e)}", exc_info=True)
            return []
    
    def _aggregate_answers(self, answers: List[Dict]) -> List[Dict]:
        """
        Aggregate and deduplicate answers from multiple chunks
        
        Args:
            answers: List of answer dictionaries
        
        Returns:
            Deduplicated and sorted list of answers
        """
        if not answers:
            return []
        
        # Group by normalized text
        text_groups = defaultdict(list)
        for ans in answers:
            normalized_text = ans["text"].lower().strip()
            text_groups[normalized_text].append(ans)
        
        # For each group, take the highest scoring instance
        final_answers = []
        for text, group in text_groups.items():
            best = max(group, key=lambda x: x["score"])
            final_answers.append(best)
        
        # Sort by confidence descending
        final_answers.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Return top 3 answers maximum
        return final_answers[:3]
    
    def _extract_clause_type(self, question: str) -> str:
        """Extract clause type from CUAD question format"""
        try:
            # Format: "Highlight the parts (if any) of this contract related to \"Clause Type\"."
            start = question.find('"') + 1
            end = question.find('"', start)
            clause_type = question[start:end]
            return clause_type
        except:
            return "Unknown"
    
    @staticmethod
    def _sigmoid(x: float) -> float:
        """Convert logit to probability using sigmoid"""
        return 1 / (1 + np.exp(-x))
