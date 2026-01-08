from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.config import settings
from app.models.schemas import ExtractionResponse, ClauseExtraction, ErrorResponse
from app.services.pdf_extractor import PDFExtractor
from app.services.clause_extractor import ClauseExtractor
from app.services.risk_scorer import RiskScorer
from app.services.rag_service import RAGService
from app.core.database import sqlite_db
from app.core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/api/extract", tags=["Extraction"])

pdf_extractor = PDFExtractor()
clause_extractor = ClauseExtractor()
risk_scorer = RiskScorer()
rag_service = RAGService()

@router.post("/{doc_id}", response_model=ExtractionResponse)
async def extract_clauses(doc_id: str):
    """
    Extract all clauses from uploaded contract and calculate risk scores
    
    - Extracts text from PDF with page mapping
    - Runs TinyRoBERTa model to extract 41 clause types
    - Calculates risk scores for each clause
    - Computes overall contract risk
    - Indexes document in ChromaDB for RAG
    - Returns comprehensive extraction results
    """
    logger.info(f"Starting clause extraction for document: {doc_id}")
    
    try:
        # Check if document exists
        pdf_path = Path(settings.UPLOAD_DIR) / f"{doc_id}.pdf"
        
        if not pdf_path.exists():
            logger.error(f"Document not found: {doc_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update status to processing
        conn = sqlite_db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE documents SET status = ? WHERE doc_id = ?",
            ("processing", doc_id)
        )
        conn.commit()
        conn.close()
        
        # Extract text with page mapping
        logger.info("Extracting text from PDF with page mapping")
        contract_text, char_to_page_map, num_pages, success = pdf_extractor.extract_text_with_page_mapping(
            str(pdf_path)
        )
        
        if not success or not contract_text:
            logger.error(f"Text extraction failed for document: {doc_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to extract text from PDF"
            )
        
        logger.info(f"Text extracted: {len(contract_text)} characters, {num_pages} pages")
        
        # Extract all clauses
        logger.info("Starting clause extraction with TinyRoBERTa model")
        extracted_clauses = clause_extractor.extract_all_clauses(
            contract_text=contract_text,
            char_to_page_map=char_to_page_map
        )
        
        logger.info(f"Clause extraction complete: {len(extracted_clauses)} clauses processed")
        
        # Score all clauses
        logger.info("Calculating risk scores")
        scored_clauses, overall_risk = risk_scorer.score_all_clauses(extracted_clauses)
        
        # Get risk summary
        risk_summary = risk_scorer.get_risk_summary(scored_clauses)
        
        # Determine overall risk level
        if overall_risk >= 60:
            risk_level = "HIGH"
        elif overall_risk >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        logger.info(f"Risk assessment complete: Overall risk = {overall_risk} ({risk_level})")
        
        # Save extracted clauses to database
        logger.info("Saving extraction results to database")
        conn = sqlite_db.get_connection()
        cursor = conn.cursor()
        
        for clause_type, clause_info in scored_clauses.items():
            cursor.execute('''
                INSERT INTO extracted_clauses 
                (doc_id, clause_type, extracted_text, confidence, risk_score, risk_level, 
                 page_number, char_start, char_end)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id,
                clause_type,
                clause_info.get("extracted_text"),
                clause_info.get("confidence"),
                clause_info.get("risk_score"),
                clause_info.get("risk_level"),
                clause_info.get("page_number"),
                clause_info.get("char_start"),
                clause_info.get("char_end")
            ))
        
        # Update document with overall risk
        cursor.execute(
            "UPDATE documents SET overall_risk_score = ?, status = ? WHERE doc_id = ?",
            (overall_risk, "completed", doc_id)
        )
        
        conn.commit()
        conn.close()
        
        # Index document in ChromaDB for RAG
        logger.info("Indexing document in ChromaDB for RAG")
        rag_service.index_document(
            doc_id=doc_id,
            contract_text=contract_text,
            extracted_clauses=scored_clauses
        )
        
        # Get original filename
        conn = sqlite_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        filename = row[0] if row else "unknown.pdf"
        conn.close()
        
        # Prepare response
        clause_list = []
        for clause_type, clause_info in scored_clauses.items():
            clause_list.append(ClauseExtraction(
                clause_type=clause_type,
                extracted_text=clause_info.get("extracted_text"),
                confidence=clause_info.get("confidence", 0.0),
                risk_score=clause_info.get("risk_score", 0.0),
                risk_level=clause_info.get("risk_level", "UNKNOWN"),
                found=clause_info.get("found", False),
                page_number=clause_info.get("page_number"),
                char_start=clause_info.get("char_start"),
                char_end=clause_info.get("char_end"),
                reliability_flag=clause_info.get("reliability_flag")
            ))
        
        response = ExtractionResponse(
            doc_id=doc_id,
            filename=filename,
            overall_risk_score=overall_risk,
            risk_level=risk_level,
            num_pages=num_pages,
            clauses=clause_list,
            high_risk_count=risk_summary["high_risk_count"],
            medium_risk_count=risk_summary["medium_risk_count"],
            low_risk_count=risk_summary["low_risk_count"],
            missing_critical_count=risk_summary["missing_critical_count"],
            timestamp=datetime.now()
        )
        
        logger.info(f"Extraction complete for document: {doc_id}")
        
        return response
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}", exc_info=True)
        
        # Update status to failed
        try:
            conn = sqlite_db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET status = ? WHERE doc_id = ?",
                ("failed", doc_id)
            )
            conn.commit()
            conn.close()
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
