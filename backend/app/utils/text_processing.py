import re
from typing import List, Tuple
from app.core.logger import get_logger
from typing import List, Dict


logger = get_logger(__name__)

class TextProcessor:
    """Utility class for text preprocessing and chunking"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean extracted PDF text by removing artifacts and normalizing whitespace
        
        Args:
            text: Raw text from PDF
        
        Returns:
            Cleaned text
        """
        try:
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove page numbers (common patterns)
            text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)
            
            # Remove common header/footer artifacts
            text = re.sub(r'^\s*-+\s*$', '', text, flags=re.MULTILINE)
            text = re.sub(r'^\s*=+\s*$', '', text, flags=re.MULTILINE)
            
            # Normalize quotes
            text = text.replace('"', '"').replace('"', '"')
            text = text.replace(''', "'").replace(''', "'")
            
            # Remove zero-width characters
            text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
            
            # Strip and ensure single spacing
            text = ' '.join(text.split())
            
            logger.debug(f"Cleaned text: {len(text)} characters")
            return text
        
        except Exception as e:
            logger.error(f"Error cleaning text: {str(e)}")
            return text
    
    @staticmethod
    def extract_sections(text: str) -> List[Tuple[str, str]]:
        """
        Attempt to extract sections from contract (e.g., Section 1, Article 2)
        
        Args:
            text: Contract text
        
        Returns:
            List of (section_name, section_text) tuples
        """
        sections = []
        
        # Common section patterns
        patterns = [
            r'(?:Section|SECTION|Article|ARTICLE)\s+(\d+\.?\d*)\s*[:\.\-]?\s*([^\n]+)',
            r'(\d+\.?\d*)\s*\.\s*([A-Z][^\n]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                section_num = match.group(1)
                section_title = match.group(2).strip()
                sections.append((f"Section {section_num}", section_title))
        
        if sections:
            logger.debug(f"Extracted {len(sections)} sections from contract")
        
        return sections
    
    @staticmethod
    def chunk_text_with_overlap(text: str, chunk_size: int, overlap: int) -> List[Dict]:
        """
        Chunk text with character-level overlap for better context preservation
        
        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters
        
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        text_length = len(text)
        start = 0
        chunk_id = 0
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk_text = text[start:end]
            
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "char_start": start,
                "char_end": end,
                "length": len(chunk_text)
            })
            
            start += (chunk_size - overlap)
            chunk_id += 1
        
        logger.info(f"Created {len(chunks)} chunks from text ({text_length} characters)")
        return chunks
