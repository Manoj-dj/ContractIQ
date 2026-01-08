import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict
from app.core.logger import get_logger

logger = get_logger(__name__)

class ExcelExporter:
    """
    Excel export service for contract analysis results
    Creates multi-sheet Excel workbook with comprehensive information
    """
    
    def export_results(self, doc_id: str, filename: str, extraction_result: Dict, 
                      output_path: str = None) -> str:
        """
        Export extraction results to Excel file
        
        Args:
            doc_id: Document identifier
            filename: Original filename
            extraction_result: Complete extraction result dictionary
            output_path: Optional custom output path
        
        Returns:
            Path to generated Excel file
        """
        logger.info(f"Exporting results for document {doc_id} to Excel")
        
        try:
            # Determine output path
            if output_path is None:
                output_dir = Path("./data/exports")
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = output_dir / f"{doc_id}_{timestamp}.xlsx"
            
            # Create Excel writer
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Sheet 1: Overview
                self._write_overview_sheet(writer, doc_id, filename, extraction_result)
                
                # Sheet 2: All Clauses
                self._write_all_clauses_sheet(writer, extraction_result)
                
                # Sheet 3: High-Risk Clauses Only
                self._write_high_risk_sheet(writer, extraction_result)
                
                # Sheet 4: Missing Critical Clauses
                self._write_missing_clauses_sheet(writer, extraction_result)
            
            logger.info(f"Excel file exported successfully: {output_path}")
            
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Failed to export to Excel: {str(e)}", exc_info=True)
            raise
    
    def _write_overview_sheet(self, writer, doc_id: str, filename: str, result: Dict):
        """Write overview summary sheet"""
        overview_data = {
            "Field": [
                "Document ID",
                "Filename",
                "Analysis Date",
                "Number of Pages",
                "Overall Risk Score",
                "Risk Level",
                "High-Risk Clauses",
                "Medium-Risk Clauses",
                "Low-Risk Clauses",
                "Missing Critical Clauses",
                "Total Clauses Analyzed"
            ],
            "Value": [
                doc_id,
                filename,
                result["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                result["num_pages"],
                f"{result['overall_risk_score']}/100",
                result["risk_level"],
                result["high_risk_count"],
                result["medium_risk_count"],
                result["low_risk_count"],
                result["missing_critical_count"],
                len(result["clauses"])
            ]
        }
        
        df_overview = pd.DataFrame(overview_data)
        df_overview.to_excel(writer, sheet_name="Overview", index=False)
        
        logger.debug("Overview sheet written")
    
    def _write_all_clauses_sheet(self, writer, result: Dict):
        """Write all clauses sheet"""
        clauses_data = []
        
        for clause in result["clauses"]:
            clauses_data.append({
                "Clause Type": clause["clause_type"],
                "Found": "Yes" if clause["found"] else "No",
                "Extracted Text": clause["extracted_text"] if clause["extracted_text"] else "Not Found",
                "Confidence": f"{clause['confidence']*100:.1f}%" if clause["found"] else "N/A",
                "Risk Score": f"{clause['risk_score']}/100",
                "Risk Level": clause["risk_level"],
                "Page Number": clause["page_number"] if clause["page_number"] else "N/A",
                "Reliability Flag": clause["reliability_flag"] if clause["reliability_flag"] else "OK"
            })
        
        df_clauses = pd.DataFrame(clauses_data)
        df_clauses.to_excel(writer, sheet_name="All Clauses", index=False)
        
        logger.debug(f"All clauses sheet written with {len(clauses_data)} rows")
    
    def _write_high_risk_sheet(self, writer, result: Dict):
        """Write high-risk clauses only"""
        high_risk_data = []
        
        for clause in result["clauses"]:
            if clause["risk_level"] == "HIGH":
                high_risk_data.append({
                    "Clause Type": clause["clause_type"],
                    "Extracted Text": clause["extracted_text"] if clause["extracted_text"] else "MISSING",
                    "Risk Score": f"{clause['risk_score']}/100",
                    "Confidence": f"{clause['confidence']*100:.1f}%" if clause["found"] else "N/A",
                    "Page Number": clause["page_number"] if clause["page_number"] else "N/A",
                    "Action Required": "REVIEW IMMEDIATELY" if clause["reliability_flag"] else "Review with legal counsel"
                })
        
        df_high_risk = pd.DataFrame(high_risk_data)
        df_high_risk.to_excel(writer, sheet_name="High-Risk Clauses", index=False)
        
        logger.debug(f"High-risk sheet written with {len(high_risk_data)} clauses")
    
    def _write_missing_clauses_sheet(self, writer, result: Dict):
        """Write missing critical clauses"""
        missing_data = []
        
        for clause in result["clauses"]:
            if not clause["found"] and clause.get("reliability_flag") == "MISSING_CRITICAL":
                missing_data.append({
                    "Clause Type": clause["clause_type"],
                    "Status": "MISSING",
                    "Risk Score": f"{clause['risk_score']}/100",
                    "Importance": "CRITICAL",
                    "Recommendation": f"Add {clause['clause_type']} clause before signing"
                })
        
        df_missing = pd.DataFrame(missing_data)
        df_missing.to_excel(writer, sheet_name="Missing Critical", index=False)
        
        logger.debug(f"Missing clauses sheet written with {len(missing_data)} items")
