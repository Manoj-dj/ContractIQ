from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage
from pathlib import Path
from typing import Tuple, Optional
import io
from app.core.logger import get_logger
from app.utils.text_processing import TextProcessor

logger = get_logger(__name__)

class PDFExtractor:
    """
    PDF text extraction service using pdfminer.six for high-quality digital PDF extraction
    Handles multi-page documents and provides page-level metadata
    """
    
    def __init__(self):
        self.text_processor = TextProcessor()
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int, bool]:
        """
        Extract text from PDF file with page count and success status
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Tuple of (extracted_text, num_pages, success)
        """
        try:
            logger.info(f"Starting PDF text extraction: {pdf_path}")
            
            # Validate file exists
            if not Path(pdf_path).exists():
                logger.error(f"PDF file not found: {pdf_path}")
                return "", 0, False
            
            # Extract text using pdfminer
            extracted_text = extract_text(pdf_path)
            
            if not extracted_text or len(extracted_text.strip()) < 100:
                logger.warning(f"Extracted text is too short or empty from {pdf_path}")
                return "", 0, False
            
            # Get page count
            num_pages = self._get_page_count(pdf_path)
            
            # Clean extracted text
            cleaned_text = self.text_processor.clean_text(extracted_text)
            
            logger.info(f"Successfully extracted {len(cleaned_text)} characters from {num_pages} pages")
            
            return cleaned_text, num_pages, True
        
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}", exc_info=True)
            return "", 0, False
    
    def extract_text_with_page_mapping(self, pdf_path: str) -> Tuple[str, dict, int, bool]:
        """
        Extract text with character-to-page mapping for location tracking
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Tuple of (full_text, char_to_page_map, num_pages, success)
        """
        try:
            logger.info(f"Extracting text with page mapping: {pdf_path}")
            
            full_text = ""
            char_to_page_map = {}
            current_char_position = 0
            page_number = 1
            
            with open(pdf_path, 'rb') as file:
                for page in PDFPage.get_pages(file):
                    # Extract text from individual page
                    page_text = extract_text(pdf_path, page_numbers=[page_number-1])
                    
                    if page_text:
                        page_text = self.text_processor.clean_text(page_text)
                        
                        # Map character positions to page numbers
                        for i in range(len(page_text)):
                            char_to_page_map[current_char_position + i] = page_number
                        
                        full_text += page_text
                        current_char_position += len(page_text)
                    
                    page_number += 1
            
            num_pages = page_number - 1
            
            logger.info(f"Extracted {len(full_text)} characters with page mapping ({num_pages} pages)")
            
            return full_text, char_to_page_map, num_pages, True
        
        except Exception as e:
            logger.error(f"Failed to extract text with page mapping: {str(e)}", exc_info=True)
            return "", {}, 0, False
    
    def _get_page_count(self, pdf_path: str) -> int:
        """Get total number of pages in PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                pages = list(PDFPage.get_pages(file))
                return len(pages)
        except Exception as e:
            logger.warning(f"Failed to get page count: {str(e)}")
            return 0
    
    def validate_pdf(self, file_path: str, max_size_mb: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF file before processing
        
        Args:
            file_path: Path to PDF file
            max_size_mb: Maximum allowed file size in MB
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path = Path(file_path)
            
            # Check file exists
            if not path.exists():
                return False, "File does not exist"
            
            # Check file extension
            if path.suffix.lower() != '.pdf':
                return False, "File is not a PDF"
            
            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                return False, f"File size ({file_size_mb:.2f} MB) exceeds limit ({max_size_mb} MB)"
            
            # Try to open and read first page
            with open(file_path, 'rb') as file:
                pages = list(PDFPage.get_pages(file, maxpages=1))
                if not pages:
                    return False, "PDF appears to be empty or corrupted"
            
            logger.info(f"PDF validation passed: {file_path}")
            return True, None
        
        except Exception as e:
            logger.error(f"PDF validation failed: {str(e)}")
            return False, f"PDF validation error: {str(e)}"
