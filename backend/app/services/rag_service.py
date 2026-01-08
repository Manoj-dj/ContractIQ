import os
import google.generativeai as genai
from typing import List, Dict, Optional
from app.config import settings
from app.core.database import chroma_db, sqlite_db
from app.core.logger import get_logger

logger = get_logger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class RAGService:
    """
    Retrieval-Augmented Generation service for conversational contract QA
    Uses ChromaDB for retrieval and Gemini 2.5 Flash lite for generation
    """
    
    def __init__(self):
        self.chroma = chroma_db
        self.sqlite = sqlite_db
        
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        logger.info("RAG service initialized with Gemini 2.5 Flash lite")
    
    def index_document(self, doc_id: str, contract_text: str, extracted_clauses: Dict[str, Dict]):
        """
        Index contract text and extracted clauses in ChromaDB
        
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
            
            # 1. Index original contract chunks
            chunk_size = 1000  # characters
            overlap = 200
            
            for i in range(0, len(contract_text), chunk_size - overlap):
                chunk_text = contract_text[i:i + chunk_size]
                
                documents.append(chunk_text)
                metadatas.append({
                    "type": "original_chunk",
                    "doc_id": doc_id,
                    "chunk_id": i // (chunk_size - overlap),
                    "char_start": i,
                    "char_end": min(i + chunk_size, len(contract_text))
                })
                ids.append(f"{doc_id}_chunk_{i}")
            
            # 2. Index extracted clauses (for metadata-filtered RAG)
            for clause_type, clause_info in extracted_clauses.items():
                if clause_info["found"] and clause_info["extracted_text"]:
                    documents.append(clause_info["extracted_text"])
                    metadatas.append({
                        "type": "extracted_clause",
                        "doc_id": doc_id,
                        "clause_type": clause_type,
                        "risk_level": clause_info["risk_level"],
                        "risk_score": clause_info["risk_score"],
                        "confidence": clause_info["confidence"],
                        "page_number": clause_info.get("page_number")
                    })
                    ids.append(f"{doc_id}_clause_{clause_type}")
            
            # Add all to ChromaDB
            self.chroma.add_documents(
                collection_name=f"contract_{doc_id}",
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully indexed {len(documents)} items for document {doc_id}")
        
        except Exception as e:
            logger.error(f"Failed to index document: {str(e)}", exc_info=True)
            raise
    
    def answer_query(self, session_id: str, doc_id: str, user_query: str) -> Dict:
        """
        Answer user query using RAG with conversational memory
        
        Args:
            session_id: Session identifier
            doc_id: Document identifier
            user_query: User's question
        
        Returns:
            Dictionary with answer, sources, and metadata
        """
        logger.info(f"Processing query for session {session_id}, doc {doc_id}")
        
        try:
            # 1. Retrieve conversation history
            history = self.sqlite.get_conversation_history(
                session_id=session_id,
                limit=settings.CONVERSATION_HISTORY_LENGTH
            )
            
            # 2. Reformulate query if needed (add context from history)
            reformulated_query = self._reformulate_query(user_query, history)
            
            # 3. Retrieve relevant chunks (metadata-filtered RAG)
            # First try to get from extracted clauses, then fallback to full text
            sources = self._retrieve_relevant_chunks(doc_id, reformulated_query)
            
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
    
    def _reformulate_query(self, query: str, history: List[Dict]) -> str:
        """
        Reformulate query based on conversation history to resolve pronouns
        
        Args:
            query: Current user query
            history: Conversation history
        
        Returns:
            Reformulated query with context
        """
        if not history:
            return query
        
        query_lower = query.lower()
        pronouns = ["it", "this", "that", "they", "these", "those"]
        
        # Check if query contains pronouns
        has_pronoun = any(pronoun in query_lower.split() for pronoun in pronouns)
        
        if not has_pronoun:
            return query
        
        # Get last 2 conversation turns for context
        recent_context = history[-2:] if len(history) >= 2 else history
        
        context_str = "\n".join([
            f"Previous Q: {turn['user_query']}\nPrevious A: {turn['ai_response']}"
            for turn in recent_context
        ])
        
        # Use Gemini to reformulate
        try:
            prompt = f"""Given the conversation history, reformulate the current question to be self-contained and clear.

Conversation History:
{context_str}

Current Question: {query}

Reformulated Question (keep it concise, add necessary context):"""
            
            response = self.model.generate_content(prompt)
            reformulated = response.text.strip()
            
            logger.debug(f"Reformulated '{query}' to '{reformulated}'")
            
            return reformulated
        
        except:
            # Fallback: just return original query
            return query
    
    def _retrieve_relevant_chunks(self, doc_id: str, query: str) -> List[Dict]:
        """
        Retrieve relevant chunks using metadata-filtered RAG
        
        Args:
            doc_id: Document identifier
            query: User query (possibly reformulated)
        
        Returns:
            List of retrieved source chunks with metadata
        """
        try:
            collection_name = f"contract_{doc_id}"
            
            # First, search in extracted clauses only
            clause_results = self.chroma.query_documents(
                collection_name=collection_name,
                query_texts=[query],
                n_results=3,
                where={"type": "extracted_clause"}
            )
            
            # Then, search in original text
            text_results = self.chroma.query_documents(
                collection_name=collection_name,
                query_texts=[query],
                n_results=settings.TOP_K_RETRIEVAL
            )
            
            # Combine and deduplicate
            sources = []
            
            # Add extracted clauses first (higher priority)
            if clause_results["documents"][0]:
                for i, doc in enumerate(clause_results["documents"][0]):
                    metadata = clause_results["metadatas"][0][i]
                    sources.append({
                        "text": doc,
                        "type": "extracted_clause",
                        "clause_type": metadata.get("clause_type"),
                        "risk_level": metadata.get("risk_level"),
                        "risk_score": metadata.get("risk_score"),
                        "page_number": metadata.get("page_number")
                    })
            
            # Add original text chunks
            if text_results["documents"][0]:
                for i, doc in enumerate(text_results["documents"][0]):
                    metadata = text_results["metadatas"][0][i]
                    if metadata.get("type") != "extracted_clause":  # Avoid duplicates
                        sources.append({
                            "text": doc,
                            "type": "original_chunk",
                            "char_start": metadata.get("char_start"),
                            "char_end": metadata.get("char_end")
                        })
            
            logger.debug(f"Retrieved {len(sources)} relevant chunks")
            
            return sources[:settings.TOP_K_RETRIEVAL]
        
        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {str(e)}")
            return []
    
    def _generate_answer(self, query: str, sources: List[Dict], history: List[Dict]) -> str:
        """
        Generate answer using Gemini with retrieved sources and history
        
        Args:
            query: User query
            sources: Retrieved source chunks
            history: Conversation history
        
        Returns:
            Generated answer
        """
        try:
            # Build context from sources
            context_parts = []
            for i, source in enumerate(sources, 1):
                if source["type"] == "extracted_clause":
                    context_parts.append(
                        f"[Extracted Clause: {source['clause_type']}]\n"
                        f"Risk Level: {source['risk_level']} ({source['risk_score']}/100)\n"
                        f"Text: {source['text']}\n"
                    )
                else:
                    context_parts.append(f"[Contract Section {i}]\n{source['text']}\n")
            
            context_str = "\n".join(context_parts)
            
            # Build conversation history
            history_str = ""
            if history:
                recent_history = history[-3:]  # Last 3 turns
                history_str = "\n".join([
                    f"User: {turn['user_query']}\nAssistant: {turn['ai_response']}"
                    for turn in recent_history
                ])
            
            # Build prompt
            prompt = f"""You are a legal contract analysis assistant. Answer the user's question based on the provided contract information.

Contract Information:
{context_str}

{f"Previous Conversation:{history_str}" if history_str else ""}

User Question: {query}

Instructions:
- Provide a clear, accurate answer based on the contract information
- If the information mentions risk levels, include them in your answer
- If you're citing a specific clause, mention its type
- If the information is insufficient, say so clearly
- Keep the answer concise and professional
- Do not make assumptions beyond what's in the contract

Answer:"""
            
            # Generate response
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            
            logger.debug(f"Generated answer: {answer[:100]}...")
            
            return answer
        
        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error while processing your question. Please try again."
