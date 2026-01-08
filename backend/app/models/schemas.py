from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class ClauseExtraction(BaseModel):
    """Schema for a single extracted clause"""
    clause_type: str = Field(..., description="Type of clause (e.g., 'Indemnity')")
    extracted_text: Optional[str] = Field(None, description="Extracted clause text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk score (0-100)")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH")
    found: bool = Field(..., description="Whether clause was found")
    page_number: Optional[int] = Field(None, description="Page number where clause appears")
    char_start: Optional[int] = Field(None, description="Character start position")
    char_end: Optional[int] = Field(None, description="Character end position")
    reliability_flag: Optional[str] = Field(None, description="Human verification flag if confidence < 0.6")

class ExtractionResponse(BaseModel):
    """Schema for complete extraction response"""
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str = Field(..., description="Overall contract risk level")
    num_pages: int = Field(..., description="Number of pages in contract")
    clauses: List[ClauseExtraction] = Field(..., description="All extracted clauses")
    high_risk_count: int = Field(..., description="Count of high-risk clauses")
    medium_risk_count: int = Field(..., description="Count of medium-risk clauses")
    low_risk_count: int = Field(..., description="Count of low-risk clauses")
    missing_critical_count: int = Field(..., description="Count of missing critical clauses")
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    """Schema for chat request"""
    session_id: str = Field(..., description="Unique session identifier")
    doc_id: str = Field(..., description="Document identifier")
    query: str = Field(..., min_length=1, max_length=500, description="User question")

class ChatResponse(BaseModel):
    """Schema for chat response"""
    session_id: str
    doc_id: str
    query: str
    reformulated_query: Optional[str] = None
    answer: str
    confidence: Optional[float] = None
    sources: List[Dict] = Field(default_factory=list, description="Retrieved source chunks")
    timestamp: datetime = Field(default_factory=datetime.now)

class UploadResponse(BaseModel):
    """Schema for upload response"""
    doc_id: str
    filename: str
    file_size: int
    num_pages: Optional[int] = None
    status: str = Field(default="uploaded")
    message: str

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
