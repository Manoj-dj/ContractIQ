from typing import Dict
from app.utils.risk_rules import RiskRules
from app.core.logger import get_logger

logger = get_logger(__name__)

class RiskScorer:
    """
    Risk assessment service for contract clauses
    Uses industry-standard rules to evaluate clause risk levels
    """
    
    def __init__(self):
        self.risk_rules = RiskRules()
    
    def score_all_clauses(self, extracted_clauses: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Score all extracted clauses and calculate overall contract risk
        
        Args:
            extracted_clauses: Dictionary of clause_type to extraction results
        
        Returns:
            Dictionary with risk scores added to each clause
        """
        logger.info("Starting risk scoring for all clauses")
        
        scored_clauses = {}
        
        for clause_type, extraction_result in extracted_clauses.items():
            extracted_text = extraction_result.get("extracted_text")
            confidence = extraction_result.get("confidence", 0.0)
            
            # Calculate risk score
            risk_score, risk_level, reliability_flag = self.risk_rules.assess_clause_risk(
                clause_type=clause_type,
                extracted_text=extracted_text,
                confidence=confidence
            )
            
            # Add risk information to result
            scored_clauses[clause_type] = {
                **extraction_result,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "reliability_flag": reliability_flag
            }
            
            logger.debug(f"{clause_type}: Risk={risk_score} ({risk_level}), Confidence={confidence:.2f}")
        
        # Calculate overall contract risk
        overall_risk = self.risk_rules.calculate_overall_risk(scored_clauses)
        
        logger.info(f"Risk scoring complete. Overall contract risk: {overall_risk}")
        
        return scored_clauses, overall_risk
    
    def get_risk_summary(self, scored_clauses: Dict[str, Dict]) -> Dict:
        """
        Generate summary statistics for risk assessment
        
        Args:
            scored_clauses: Dictionary of scored clauses
        
        Returns:
            Dictionary with risk summary statistics
        """
        high_risk_count = sum(1 for c in scored_clauses.values() if c["risk_level"] == "HIGH")
        medium_risk_count = sum(1 for c in scored_clauses.values() if c["risk_level"] == "MEDIUM")
        low_risk_count = sum(1 for c in scored_clauses.values() if c["risk_level"] == "LOW")
        missing_critical_count = sum(
            1 for c in scored_clauses.values() 
            if c.get("reliability_flag") == "MISSING_CRITICAL"
        )
        found_count = sum(1 for c in scored_clauses.values() if c["found"])
        
        summary = {
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "low_risk_count": low_risk_count,
            "missing_critical_count": missing_critical_count,
            "found_count": found_count,
            "total_clauses": len(scored_clauses)
        }
        
        logger.info(f"Risk summary: {summary}")
        
        return summary
