import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class SQLiteDB:
    """SQLite database manager for conversation history"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    user_query TEXT NOT NULL,
                    reformulated_query TEXT,
                    ai_response TEXT NOT NULL,
                    confidence REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, turn_number)
                )
            ''')
            
            # Documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    num_pages INTEGER,
                    overall_risk_score REAL,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            # Extracted clauses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS extracted_clauses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    clause_type TEXT NOT NULL,
                    extracted_text TEXT,
                    confidence REAL,
                    risk_score REAL,
                    risk_level TEXT,
                    page_number INTEGER,
                    char_start INTEGER,
                    char_end INTEGER,
                    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("SQLite database initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {str(e)}")
            raise
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def save_conversation_turn(self, session_id: str, doc_id: str, turn_number: int,
                               user_query: str, ai_response: str, 
                               reformulated_query: str = None, confidence: float = None):
        """Save a conversation turn"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO conversations 
                (session_id, doc_id, turn_number, user_query, reformulated_query, ai_response, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, doc_id, turn_number, user_query, reformulated_query, ai_response, confidence))
            
            conn.commit()
            conn.close()
            logger.debug(f"Saved conversation turn {turn_number} for session {session_id}")
        
        except Exception as e:
            logger.error(f"Failed to save conversation turn: {str(e)}")
            raise
    
    def get_conversation_history(self, session_id: str, limit: int = None) -> List[Dict]:
        """Retrieve conversation history for a session"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            limit_clause = f"LIMIT {limit}" if limit else ""
            cursor.execute(f'''
                SELECT turn_number, user_query, reformulated_query, ai_response, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY turn_number DESC
                {limit_clause}
            ''', (session_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = [
                {
                    "turn": row[0],
                    "user_query": row[1],
                    "reformulated_query": row[2],
                    "ai_response": row[3],
                    "timestamp": row[4]
                }
                for row in reversed(rows)
            ]
            
            return history
        
        except Exception as e:
            logger.error(f"Failed to retrieve conversation history: {str(e)}")
            return []


class ChromaDBManager:
    """ChromaDB manager for vector storage and retrieval"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        logger.info("ChromaDB client initialized")
    
    def get_or_create_collection(self, collection_name: str):
        """Get or create a ChromaDB collection"""
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Contract text and extracted clauses"}
            )
            logger.info(f"Collection '{collection_name}' ready")
            return collection
        
        except Exception as e:
            logger.error(f"Failed to create/get collection: {str(e)}")
            raise
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadatas: List[Dict], ids: List[str]):
        """Add documents to collection"""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to collection '{collection_name}'")
        
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {str(e)}")
            raise
    
    def query_documents(self, collection_name: str, query_texts: List[str], 
                       n_results: int = 5, where: Dict = None) -> Dict:
        """Query documents from collection"""
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where
            )
            logger.debug(f"Retrieved {len(results['documents'][0])} results from '{collection_name}'")
            return results
        
        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {str(e)}")
            raise


# Singleton instances
sqlite_db = SQLiteDB()
chroma_db = ChromaDBManager()
