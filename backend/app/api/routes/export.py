from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from app.services.excel_exporter import ExcelExporter
from app.core.database import sqlite_db
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/export", tags=["Export"])

excel_exporter = ExcelExporter()

@router.get("/{doc_id}")
async def export_to_excel(doc_id: str):
    """
    Export contract analysis results to Excel file
    
    - Retrieves extraction results from database
    - Generates multi-sheet Excel workbook
    - Includes overview, all clauses, high-risk clauses, and missing clauses
    - Returns downloadable file
    """
    logger.info(f"Export request for document: {doc_id}")
    
    try:
        # Retrieve document info
        conn = sqlite_db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, num_pages, overall_risk_score FROM documents WHERE doc_id = ?",
            (doc_id,)
        )
        doc_row = cursor.fetchone()
        
        if not doc_row:
            logger.error(f"Document not found: {doc_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        filename, num_pages, overall_risk_score = doc_row
        
        # Retrieve extracted clauses
        cursor.execute(
            "SELECT clause_type, extracted_text, confidence, risk_score, risk_level, "
            "page_number, char_start, char_end FROM extracted_clauses WHERE doc_id = ?",
            (doc_id,)
        )
        clause_rows = cursor.fetchall()
        
        conn.close()
        
        if not clause_rows:
            logger.error(f"No extraction results found for document: {doc_id}")
            raise HTTPException(
                status_code=404,
                detail="No extraction results found. Please extract clauses first."
            )
        
        # Prepare extraction result dictionary
        clauses = []
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        missing_critical_count = 0
        
        for row in clause_rows:
            clause_type, extracted_text, confidence, risk_score, risk_level, page_number, char_start, char_end = row
            
            found = extracted_text is not None
            reliability_flag = None
            
            if not found and risk_score >= 60:
                reliability_flag = "MISSING_CRITICAL"
                missing_critical_count += 1
            
            if confidence and confidence < 0.6 and risk_score >= 60:
                reliability_flag = "REQUIRES_HUMAN_VERIFICATION"
            
            clauses.append({
                "clause_type": clause_type,
                "extracted_text": extracted_text,
                "confidence": confidence or 0.0,
                "risk_score": risk_score or 0.0,
                "risk_level": risk_level or "UNKNOWN",
                "found": found,
                "page_number": page_number,
                "char_start": char_start,
                "char_end": char_end,
                "reliability_flag": reliability_flag
            })
            
            if risk_level == "HIGH":
                high_risk_count += 1
            elif risk_level == "MEDIUM":
                medium_risk_count += 1
            elif risk_level == "LOW":
                low_risk_count += 1
        
        # Determine overall risk level
        if overall_risk_score >= 60:
            risk_level = "HIGH"
        elif overall_risk_score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        from datetime import datetime
        extraction_result = {
            "doc_id": doc_id,
            "filename": filename,
            "num_pages": num_pages,
            "overall_risk_score": overall_risk_score,
            "risk_level": risk_level,
            "clauses": clauses,
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "low_risk_count": low_risk_count,
            "missing_critical_count": missing_critical_count,
            "timestamp": datetime.now()
        }
        
        # Generate Excel file
        logger.info("Generating Excel file")
        excel_path = excel_exporter.export_results(
            doc_id=doc_id,
            filename=filename,
            extraction_result=extraction_result
        )
        
        logger.info(f"Excel file generated: {excel_path}")
        
        # Return file as download
        return FileResponse(
            path=excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{filename.replace('.pdf', '')}_analysis.xlsx"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
