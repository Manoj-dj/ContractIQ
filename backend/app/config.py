import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import os
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

# Load environment variables
load_dotenv()

class Settings:
    """Application configuration settings loaded from environment variables"""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Model Configuration
    MODEL_PATH: str = os.getenv("MODEL_PATH", "../checkpoint-4089")
    DEVICE: str = os.getenv("DEVICE", "cpu")
    
    # Application Settings
    APP_NAME: str = os.getenv("APP_NAME", "ContractIQ")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # File Upload Settings
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: list = os.getenv("ALLOWED_EXTENSIONS", "pdf").split(",")
    
    # Inference Settings
    MAX_LENGTH: int = int(os.getenv("MAX_LENGTH", "512"))
    STRIDE: int = int(os.getenv("STRIDE", "128"))
    NULL_THRESHOLD: float = float(os.getenv("NULL_THRESHOLD", "0.0"))
    N_BEST: int = 5
    MAX_ANSWER_LENGTH: int = 200
    
    # RAG Settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "15"))
    CONVERSATION_HISTORY_LENGTH: int = int(os.getenv("CONVERSATION_HISTORY_LENGTH", "10"))
    
    # Database Paths
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./data/chroma")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./data/database.db")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")
    
    # CUAD Questions (41 clause types)
    CUAD_QUESTIONS: list = [
        "Highlight the parts (if any) of this contract related to \"Document Name\".",
        "Highlight the parts (if any) of this contract related to \"Parties\".",
        "Highlight the parts (if any) of this contract related to \"Agreement Date\".",
        "Highlight the parts (if any) of this contract related to \"Effective Date\".",
        "Highlight the parts (if any) of this contract related to \"Expiration Date\".",
        "Highlight the parts (if any) of this contract related to \"Renewal Term\".",
        "Highlight the parts (if any) of this contract related to \"Notice Period To Terminate Renewal\".",
        "Highlight the parts (if any) of this contract related to \"Governing Law\".",
        "Highlight the parts (if any) of this contract related to \"Most Favored Nation\".",
        "Highlight the parts (if any) of this contract related to \"Non-Compete\".",
        "Highlight the parts (if any) of this contract related to \"Exclusivity\".",
        "Highlight the parts (if any) of this contract related to \"No-Solicit Of Customers\".",
        "Highlight the parts (if any) of this contract related to \"No-Solicit Of Employees\".",
        "Highlight the parts (if any) of this contract related to \"Non-Disparagement\".",
        "Highlight the parts (if any) of this contract related to \"Termination For Convenience\".",
        "Highlight the parts (if any) of this contract related to \"Rofr/Rofo/Rofn\".",
        "Highlight the parts (if any) of this contract related to \"Change Of Control\".",
        "Highlight the parts (if any) of this contract related to \"Anti-Assignment\".",
        "Highlight the parts (if any) of this contract related to \"Revenue/Profit Sharing\".",
        "Highlight the parts (if any) of this contract related to \"Price Restrictions\".",
        "Highlight the parts (if any) of this contract related to \"Minimum Commitment\".",
        "Highlight the parts (if any) of this contract related to \"Volume Restriction\".",
        "Highlight the parts (if any) of this contract related to \"IP Ownership Assignment\".",
        "Highlight the parts (if any) of this contract related to \"Joint IP Ownership\".",
        "Highlight the parts (if any) of this contract related to \"License Grant\".",
        "Highlight the parts (if any) of this contract related to \"Non-Transferable License\".",
        "Highlight the parts (if any) of this contract related to \"Affiliate License-Licensor\".",
        "Highlight the parts (if any) of this contract related to \"Affiliate License-Licensee\".",
        "Highlight the parts (if any) of this contract related to \"Unlimited/All-You-Can-Eat-License\".",
        "Highlight the parts (if any) of this contract related to \"Irrevocable Or Perpetual License\".",
        "Highlight the parts (if any) of this contract related to \"Source Code Escrow\".",
        "Highlight the parts (if any) of this contract related to \"Post-Termination Services\".",
        "Highlight the parts (if any) of this contract related to \"Audit Rights\".",
        "Highlight the parts (if any) of this contract related to \"Uncapped Liability\".",
        "Highlight the parts (if any) of this contract related to \"Cap On Liability\".",
        "Highlight the parts (if any) of this contract related to \"Liquidated Damages\".",
        "Highlight the parts (if any) of this contract related to \"Warranty Duration\".",
        "Highlight the parts (if any) of this contract related to \"Insurance\".",
        "Highlight the parts (if any) of this contract related to \"Covenant Not To Sue\".",
        "Highlight the parts (if any) of this contract related to \"Third Party Beneficiary\".",
        "Highlight the parts (if any) of this contract related to \"Indemnity\".",
    ]
    
    @classmethod 
    def create_directories(cls):
        """Create necessary directories if they don't exist"""
        Path(cls.CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
        Path(cls.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(cls.LOG_DIR).mkdir(parents=True, exist_ok=True)
        Path(cls.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment variables")
        
        if not Path(cls.MODEL_PATH).exists():
            raise ValueError(f"Model path does not exist: {cls.MODEL_PATH}")

settings = Settings()
settings.create_directories()
