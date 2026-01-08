import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from typing import List, Dict, Tuple
from collections import defaultdict
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class ClauseExtractor:
    """
    Contract clause extraction service using fine-tuned TinyRoBERTa model
    Handles tokenization, chunking, inference, and answer aggregation
    """
    
    def __init__(self):
        self.model_path = settings.MODEL_PATH
        self.device = settings.DEVICE
        self.max_length = settings.MAX_LENGTH
        self.stride = settings.STRIDE
        self.null_threshold = settings.NULL_THRESHOLD
        self.n_best = settings.N_BEST
        self.max_answer_length = settings.MAX_ANSWER_LENGTH
        
        logger.info(f"Initializing ClauseExtractor with model: {self.model_path}")
        
        # Load model and tokenizer
        self._load_model()
    
    def _load_model(self):
        """Load model and tokenizer from checkpoint"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForQuestionAnswering.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"Model loaded successfully on device: {self.device}")
        
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}", exc_info=True)
            raise
    
    def extract_all_clauses(self, contract_text: str, char_to_page_map: dict = None) -> Dict[str, Dict]:
        """
        Extract all 41 CUAD clause types from contract
        
        Args:
            contract_text: Full contract text
            char_to_page_map: Optional mapping of character positions to page numbers
        
        Returns:
            Dictionary mapping clause_type to extraction results
        """
        logger.info(f"Starting extraction of {len(settings.CUAD_QUESTIONS)} clause types")
        
        results = {}
        
        for question in settings.CUAD_QUESTIONS:
            # Extract clause type from question
            clause_type = self._extract_clause_type(question)
            
            logger.debug(f"Extracting clause: {clause_type}")
            
            # Extract clause
            answers = self._answer_question(question, contract_text, char_to_page_map)
            
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
                    "all_answers": answers  # Keep all for debugging
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
        
        logger.info(f"Extraction complete. Found {sum(1 for r in results.values() if r['found'])} clauses")
        
        return results
    
    def _answer_question(self, question: str, context: str, char_to_page_map: dict = None) -> List[Dict]:
        """
        Answer a single question using the model with chunking and aggregation
        
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
                        
                        if offsets[start_idx] is None or offsets[end_idx] is None:
                            continue
                        
                        length = end_idx - start_idx + 1
                        if length > self.max_answer_length:
                            continue
                        
                        # Extract span
                        start_char = int(offsets[start_idx][0])
                        end_char = int(offsets[end_idx][1])
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
                            
                            all_answers.append({
                                "text": text,
                                "score": float(span_score),
                                "confidence": float(self._sigmoid(confidence_delta)),
                                "char_start": start_char,
                                "char_end": end_char,
                                "page_number": page_number
                            })
            
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
