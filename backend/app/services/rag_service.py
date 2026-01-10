import os
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
from app.config import settings
from app.core.database import chroma_db, sqlite_db
from app.core.logger import get_logger
import re

logger = get_logger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class RAGService:
    """
    Enhanced Retrieval-Augmented Generation service with multi-stage retrieval
    Uses ChromaDB for retrieval and Gemini 2.5 Flash for generation
    """
    
    def __init__(self):
        self.chroma = chroma_db
        self.sqlite = sqlite_db
        
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Clause type mapping for query understanding
        self.clause_keywords = {
            "Agreement Date": ["agreement date", "contract date", "signing date", "execution date"],
            "Effective Date": ["effective date", "commencement date", "start date"],
            "Expiration Date": ["expiration date", "expiry date", "end date", "termination date"],
            "Parties": ["parties", "party names", "who are the parties", "contracting parties"],
            "Governing Law": ["governing law", "applicable law", "jurisdiction", "which law applies"],
            "Termination For Convenience": ["termination", "cancel", "exit", "terminate"],
            "Notice Period To Terminate Renewal": ["notice period", "termination notice", "cancellation notice"],
            "Indemnity": ["indemnity", "indemnification", "liability protection"],
            "Cap On Liability": ["liability cap", "liability limit", "maximum liability"],
            "Uncapped Liability": ["uncapped liability", "unlimited liability"],
            "License Grant": ["license", "license grant", "usage rights"],
            "IP Ownership Assignment": ["ip ownership", "intellectual property", "ip rights"],
            "Non-Compete": ["non-compete", "non compete", "competition restriction"],
            "Confidentiality": ["confidentiality", "confidential", "nda"],
            "Auto-Renewal": ["auto renewal", "automatic renewal", "renewal"],
            "Payment Terms": ["payment", "fees", "pricing"],
            "Warranty": ["warranty", "warranties", "guarantee"],
            "Audit Rights": ["audit", "audit rights", "inspection rights"],
            "Force Majeure": ["force majeure", "act of god"],
            "Dispute Resolution": ["dispute", "arbitration", "litigation"],
        }
        
        logger.info("RAG service initialized with Gemini 2.5 Flash")
    
    def index_document(self, doc_id: str, contract_text: str, extracted_clauses: Dict[str, Dict]):
        """
        Index contract text and extracted clauses in ChromaDB with enhanced metadata
        
        Args:
            doc_id: Document identifier
            contract_text: Full contract text
            extracted_clauses: Dictionary of extracted clauses with metadata
        """
        logger.info(f"Indexing document {doc_id} in ChromaDB")
        
        try:
            collection = self.chroma.get_or_create_collection(f"contract_{doc_id}")
            
            documents = []
            metadatas = []
            ids = []
            
            # 1. Index extracted clauses FIRST (highest priority)
            for clause_type, clause_info in extracted_clauses.items():
                if clause_info["found"] and clause_info["extracted_text"]:
                    # Add clause with full metadata
                    documents.append(clause_info["extracted_text"])
                    metadatas.append({
                        "type": "extracted_clause",
                        "doc_id": doc_id,
                        "clause_type": clause_type,
                        "clause_type_lower": clause_type.lower(),  # For matching
                        "risk_level": clause_info["risk_level"],
                        "risk_score": float(clause_info["risk_score"]),
                        "confidence": float(clause_info["confidence"]),
                        "page_number": clause_info.get("page_number", 0),
                        "found": True
                    })
                    ids.append(f"{doc_id}_clause_{clause_type.replace(' ', '_')}")
            
            # 2. Index original contract in smaller, overlapping chunks for better retrieval
            chunk_size = 800  # Smaller chunks for more precise retrieval
            overlap = 200
            
            chunk_id = 0
            for i in range(0, len(contract_text), chunk_size - overlap):
                chunk_text = contract_text[i:i + chunk_size]
                
                if len(chunk_text.strip()) < 50:  # Skip tiny chunks
                    continue
                
                documents.append(chunk_text)
                metadatas.append({
                    "type": "original_chunk",
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "char_start": i,
                    "char_end": min(i + chunk_size, len(contract_text))
                })
                ids.append(f"{doc_id}_chunk_{chunk_id}")
                chunk_id += 1
            
            # 3. Index full contract text as well (for broad searches)
            documents.append(contract_text[:10000])  # First 10k chars as overview
            metadatas.append({
                "type": "full_text_preview",
                "doc_id": doc_id,
                "length": len(contract_text)
            })
            ids.append(f"{doc_id}_fulltext_preview")
            
            # Add all to ChromaDB
            self.chroma.add_documents(
                collection_name=f"contract_{doc_id}",
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully indexed {len(documents)} items for document {doc_id}")
            logger.info(f"  - Extracted clauses: {sum(1 for m in metadatas if m['type'] == 'extracted_clause')}")
            logger.info(f"  - Original chunks: {sum(1 for m in metadatas if m['type'] == 'original_chunk')}")
            logger.info(f"  - Full text preview: {sum(1 for m in metadatas if m['type'] == 'full_text_preview')}")
        
        except Exception as e:
            logger.error(f"Failed to index document: {str(e)}", exc_info=True)
            raise
    
    def answer_query(self, session_id: str, doc_id: str, user_query: str) -> Dict:
        """
        Answer user query using enhanced multi-stage RAG with conversational memory
        
        Args:
            session_id: Session identifier
            doc_id: Document identifier
            user_query: User's question
        
        Returns:
            Dictionary with answer, sources, and metadata
        """
        logger.info(f"Processing query for session {session_id}, doc {doc_id}: '{user_query}'")
        
        try:
            # 1. Retrieve conversation history
            history = self.sqlite.get_conversation_history(
                session_id=session_id,
                limit=settings.CONVERSATION_HISTORY_LENGTH
            )
            
            # 2. Reformulate query if needed (add context from history)
            reformulated_query = self._reformulate_query(user_query, history)
            logger.debug(f"Reformulated query: '{reformulated_query}'")
            
            # 3. ENHANCED MULTI-STAGE RETRIEVAL
            sources = self._retrieve_relevant_chunks_enhanced(doc_id, reformulated_query, user_query)
            
            logger.info(f"Retrieved {len(sources)} sources for query")
            
            # 4. Generate answer using Gemini
            answer = self._generate_answer(reformulated_query, sources, history)
            
            # 5. Save conversation turn
            turn_number = len(history) + 1
            self.sqlite.save_conversation_turn(
                session_id=session_id,
                doc_id=doc_id,
                turn_number=turn_number,
                user_query=user_query,
                ai_response=answer,
                reformulated_query=reformulated_query if reformulated_query != user_query else None
            )
            
            logger.info(f"Query answered successfully (turn {turn_number})")
            
            return {
                "answer": answer,
                "sources": sources,
                "reformulated_query": reformulated_query if reformulated_query != user_query else None,
                "turn_number": turn_number
            }
        
        except Exception as e:
            logger.error(f"Failed to answer query: {str(e)}", exc_info=True)
            raise
    
    def _detect_clause_types(self, query: str) -> List[str]:
        """
        Detect which clause types the user is asking about based on keywords
        
        Args:
            query: User query
        
        Returns:
            List of detected clause types
        """
        query_lower = query.lower()
        detected_clauses = []
        
        for clause_type, keywords in self.clause_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    detected_clauses.append(clause_type)
                    logger.debug(f"Detected clause type '{clause_type}' from keyword '{keyword}'")
                    break
        
        return detected_clauses
    
    def _retrieve_relevant_chunks_enhanced(self, doc_id: str, reformulated_query: str, original_query: str) -> List[Dict]:
        """
        ENHANCED MULTI-STAGE RETRIEVAL with prioritization (FIXED ChromaDB syntax)
        """
        try:
            collection_name = f"contract_{doc_id}"
            all_sources = []
            seen_texts = set()
            
            # STAGE 1: Exact clause type matching
            detected_clause_types = self._detect_clause_types(original_query)
            
            if detected_clause_types:
                logger.info(f"Stage 1: Detected clause types: {detected_clause_types}")
                
                for clause_type in detected_clause_types:
                    try:
                        # FIXED: Proper ChromaDB where syntax
                        exact_match_results = self.chroma.query_documents(
                            collection_name=collection_name,
                            query_texts=[clause_type],
                            n_results=2,
                            where={
                                "$and": [
                                    {"type": {"$eq": "extracted_clause"}},
                                    {"clause_type": {"$eq": clause_type}}
                                ]
                            }
                        )
                        
                        if exact_match_results["documents"][0]:
                            for i, doc in enumerate(exact_match_results["documents"][0]):
                                metadata = exact_match_results["metadatas"][0][i]
                                
                                if doc not in seen_texts:
                                    all_sources.append({
                                        "text": doc,
                                        "type": "extracted_clause",
                                        "clause_type": metadata.get("clause_type"),
                                        "risk_level": metadata.get("risk_level"),
                                        "risk_score": metadata.get("risk_score"),
                                        "page_number": metadata.get("page_number"),
                                        "confidence": metadata.get("confidence"),
                                        "priority": 1
                                    })
                                    seen_texts.add(doc)
                                    logger.debug(f"Stage 1: Added exact match for '{clause_type}'")
                    except Exception as e:
                        logger.warning(f"Stage 1 failed for '{clause_type}': {str(e)}")
            
            # STAGE 2: Semantic search on extracted clauses (FIXED)
            logger.info("Stage 2: Semantic search on extracted clauses")
            try:
                clause_results = self.chroma.query_documents(
                    collection_name=collection_name,
                    query_texts=[reformulated_query],
                    n_results=5,
                    where={"type": {"$eq": "extracted_clause"}}
                )
                
                if clause_results["documents"][0]:
                    for i, doc in enumerate(clause_results["documents"][0]):
                        metadata = clause_results["metadatas"][0][i]
                        
                        if doc not in seen_texts:
                            all_sources.append({
                                "text": doc,
                                "type": "extracted_clause",
                                "clause_type": metadata.get("clause_type"),
                                "risk_level": metadata.get("risk_level"),
                                "risk_score": metadata.get("risk_score"),
                                "page_number": metadata.get("page_number"),
                                "confidence": metadata.get("confidence"),
                                "priority": 2
                            })
                            seen_texts.add(doc)
                            logger.debug(f"Stage 2: Added clause '{metadata.get('clause_type')}'")
            except Exception as e:
                logger.warning(f"Stage 2 failed: {str(e)}")
            
            # STAGE 3: Semantic search on original text (FIXED)
            logger.info("Stage 3: Semantic search on original text")
            try:
                text_results = self.chroma.query_documents(
                    collection_name=collection_name,
                    query_texts=[reformulated_query],
                    n_results=8,
                    where={"type": {"$eq": "original_chunk"}}
                )
                
                if text_results["documents"][0]:
                    for i, doc in enumerate(text_results["documents"][0]):
                        metadata = text_results["metadatas"][0][i]
                        
                        if doc not in seen_texts:
                            all_sources.append({
                                "text": doc,
                                "type": "original_chunk",
                                "char_start": metadata.get("char_start"),
                                "char_end": metadata.get("char_end"),
                                "priority": 3
                            })
                            seen_texts.add(doc)
                            logger.debug(f"Stage 3: Added original chunk {metadata.get('chunk_id')}")
            except Exception as e:
                logger.warning(f"Stage 3 failed: {str(e)}")
            
            # STAGE 4: Broad search if needed
            if len(all_sources) < 5:
                logger.info("Stage 4: Broad semantic search (fallback)")
                try:
                    broad_results = self.chroma.query_documents(
                        collection_name=collection_name,
                        query_texts=[reformulated_query],
                        n_results=10
                    )
                    
                    if broad_results["documents"][0]:
                        for i, doc in enumerate(broad_results["documents"][0]):
                            metadata = broad_results["metadatas"][0][i]
                            
                            if doc not in seen_texts:
                                all_sources.append({
                                    "text": doc,
                                    "type": metadata.get("type", "unknown"),
                                    "clause_type": metadata.get("clause_type"),
                                    "risk_level": metadata.get("risk_level"),
                                    "priority": 4
                                })
                                seen_texts.add(doc)
                except Exception as e:
                    logger.warning(f"Stage 4 failed: {str(e)}")
            
            # Sort by priority
            all_sources.sort(key=lambda x: x.get("priority", 999))
            final_sources = all_sources[:10]
            
            logger.info(f"Multi-stage retrieval complete: {len(final_sources)} sources")
            logger.info(f"  - Priority 1 (Exact match): {sum(1 for s in final_sources if s.get('priority') == 1)}")
            logger.info(f"  - Priority 2 (Clause semantic): {sum(1 for s in final_sources if s.get('priority') == 2)}")
            logger.info(f"  - Priority 3 (Text semantic): {sum(1 for s in final_sources if s.get('priority') == 3)}")
            logger.info(f"  - Priority 4 (Broad fallback): {sum(1 for s in final_sources if s.get('priority') == 4)}")
            
            return final_sources
        
        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {str(e)}", exc_info=True)
            return []

    
    def _reformulate_query(self, query: str, history: List[Dict]) -> str:
        """
        Reformulate query based on conversation history to resolve pronouns
        
        Args:
            query: Current user query
            history: Conversation history
        
        Returns:
            Reformulated query with context
        """
        if not history or len(history) == 0:
            return query
        
        query_lower = query.lower()
        pronouns = ["it", "this", "that", "they", "these", "those", "he", "she"]
        
        # Check if query contains pronouns or is very short
        has_pronoun = any(pronoun in query_lower.split() for pronoun in pronouns)
        
        if not has_pronoun and len(query.split()) > 3:
            return query
        
        # Get last 2 conversation turns for context
        recent_context = history[-2:] if len(history) >= 2 else history
        
        if not recent_context:
            return query
        
        context_str = "\n".join([
            f"Q: {turn['user_query']}\nA: {turn['ai_response']}"
            for turn in recent_context
        ])
        
        # Use Gemini to reformulate only if needed
        try:
            prompt = f"""Reformulate this question to be self-contained by adding context from the conversation history. Keep it concise.

Conversation:
{context_str}

Current Question: {query}

Reformulated Question:"""
            
            response = self.model.generate_content(prompt)
            reformulated = response.text.strip()
            
            logger.debug(f"Reformulated '{query}' to '{reformulated}'")
            
            return reformulated
        
        except Exception as e:
            logger.warning(f"Reformulation failed: {str(e)}")
            return query
    
    def _generate_answer(self, query: str, sources: List[Dict], history: List[Dict]) -> str:
        """
        Generate answer using Gemini with retrieved sources and history
        
        Args:
            query: User query
            sources: Retrieved source chunks (prioritized)
            history: Conversation history
        
        Returns:
            Generated answer
        """
        try:
            # Build context from sources (with priority indicators)
            context_parts = []
            
            for i, source in enumerate(sources, 1):
                if source["type"] == "extracted_clause":
                    context_parts.append(
                        f"[Extracted Clause {i}: {source['clause_type']}]\n"
                        f"Text: {source['text']}\n"
                        f"Risk: {source['risk_level']} ({source['risk_score']}/100)\n"
                        f"Confidence: {source.get('confidence', 0)*100:.0f}%\n"
                        f"Page: {source.get('page_number', 'N/A')}\n"
                    )
                else:
                    context_parts.append(
                        f"[Contract Text Section {i}]\n"
                        f"{source['text']}\n"
                    )
            
            context_str = "\n".join(context_parts)
            
            # Build conversation history
            history_str = ""
            if history and len(history) > 0:
                recent_history = history[-3:]  # Last 3 turns
                history_str = "\n".join([
                    f"User: {turn['user_query']}\nAssistant: {turn['ai_response']}"
                    for turn in recent_history
                ])
            
            history_block = ""
            if history_str:
                history_block = "CONVERSATION HISTORY:\n" + history_str + "\n"

            prompt = f"""You are a professional legal contract assistant with expertise in contract analysis. Your goal is to provide helpful, detailed, and conversational responses about contracts.

            CONTRACT INFORMATION:
            {context_str}

            {history_block}
            USER QUESTION: {query}

            INSTRUCTIONS:
            1. **Conversational Tone**: Respond naturally like ChatGPT or Gemini would - be friendly, clear, and detailed
            2. **Comprehensive Answers**: Provide full context and explanations, not just one-line answers
            3. **Structured Response**:
            - Start with a direct answer to the question
            - Provide relevant background and explanation
            - Add context about why this matters or what it means
            - If citing specific clauses, mention them naturally in the response
            4. **Use Retrieved Information**: Base your answer on the contract information provided above
            5. **General Knowledge**: You can add general legal context or explanations to make answers more helpful
            6. **Citations**: At the end, add a brief "Source" line mentioning relevant clauses and pages
            7. **Formatting**: Write in clear paragraphs. Use plain text (no markdown bold/italic). Use line breaks for readability.
            8. **If Information Missing**: If the answer isn't in the provided contract sections, say so clearly but still provide helpful contexts

            ANSWER:"""

            
            # Generate response
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            
            logger.debug(f"Generated answer: {answer[:150]}...")
            
            return answer
        
        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error while processing your question. Please try again."
