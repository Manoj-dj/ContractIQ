from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid
import shutil
from app.config import settings
from app.models.schemas import UploadResponse, ErrorResponse
from app.services.pdf_extractor import PDFExtractor
from app.core.database import sqlite_db
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/upload", tags=["Upload"])

pdf_extractor = PDFExtractor()

@router.post("/", response_model=UploadResponse)
async def upload_contract(file: UploadFile = File(...)):
    """
    Upload a contract PDF file for processing
    
    - Validates file format and size
    - Saves file to uploads directory
    - Extracts basic metadata
    - Returns document ID for subsequent operations
    """
    logger.info(f"Received upload request: {file.filename}")
    
    try:
        # Validate file extension
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type uploaded: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )
        
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_path = Path(settings.UPLOAD_DIR) / f"{doc_id}.pdf"
        
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = upload_path.stat().st_size
        
        logger.info(f"File saved: {upload_path} ({file_size} bytes)")
        
        # Validate PDF
        is_valid, error_msg = pdf_extractor.validate_pdf(
            str(upload_path),
            max_size_mb=settings.MAX_FILE_SIZE_MB
        )
        
        if not is_valid:
            # Clean up invalid file
            upload_path.unlink()
            logger.error(f"PDF validation failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Quick extraction to get page count
        _, num_pages, success = pdf_extractor.extract_text_from_pdf(str(upload_path))
        
        if not success:
            logger.error(f"Failed to extract text from PDF: {doc_id}")
            raise HTTPException(
                status_code=400,
                detail="Failed to extract text from PDF. File may be corrupted or scanned."
            )
        
        # Save document metadata to database
        conn = sqlite_db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (doc_id, filename, num_pages, status) VALUES (?, ?, ?, ?)",
            (doc_id, file.filename, num_pages, "uploaded")
        )
        conn.commit()
        conn.close()
        
        logger.info(f"Document uploaded successfully: {doc_id}")
        
        return UploadResponse(
            doc_id=doc_id,
            filename=file.filename,
            file_size=file_size,
            num_pages=num_pages,
            status="uploaded",
            message=f"File uploaded successfully. {num_pages} pages detected."
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
