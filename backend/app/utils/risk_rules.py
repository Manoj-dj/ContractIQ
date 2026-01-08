from typing import Dict, Tuple
import re

class RiskRules:
    """
    Industry-standard risk assessment rules for contract clauses
    Risk scoring does NOT multiply by confidence to avoid underestimating critical risks
    """
    
    # Importance weights for each clause type (0.2 to 1.0)
    IMPORTANCE_WEIGHTS = {
        "Indemnity": 1.0,
        "Cap On Liability": 1.0,
        "Uncapped Liability": 1.0,
        "Liquidated Damages": 0.9,
        "Termination For Convenience": 0.9,
        "Governing Law": 0.8,
        "IP Ownership Assignment": 0.9,
        "Joint IP Ownership": 0.9,
        "Non-Compete": 0.8,
        "Exclusivity": 0.8,
        "Auto-Renewal": 0.8,
        "Change Of Control": 0.8,
        "Anti-Assignment": 0.7,
        "Audit Rights": 0.6,
        "Warranty Duration": 0.6,
        "Insurance": 0.6,
        "Notice Period To Terminate Renewal": 0.7,
        "Post-Termination Services": 0.6,
        "Revenue/Profit Sharing": 0.7,
        "Price Restrictions": 0.6,
        "Minimum Commitment": 0.6,
        "Volume Restriction": 0.5,
        "No-Solicit Of Customers": 0.7,
        "No-Solicit Of Employees": 0.7,
        "Non-Disparagement": 0.5,
        "Rofr/Rofo/Rofn": 0.7,
        "License Grant": 0.6,
        "Non-Transferable License": 0.5,
        "Irrevocable Or Perpetual License": 0.6,
        "Source Code Escrow": 0.5,
        "Covenant Not To Sue": 0.6,
        "Third Party Beneficiary": 0.5,
        "Document Name": 0.2,
        "Parties": 0.3,
        "Agreement Date": 0.2,
        "Effective Date": 0.3,
        "Expiration Date": 0.4,
        "Renewal Term": 0.5,
        "Affiliate License-Licensor": 0.4,
        "Affiliate License-Licensee": 0.4,
        "Unlimited/All-You-Can-Eat-License": 0.5,
        "Most Favored Nation": 0.6,
    }
    
    @staticmethod
    def assess_clause_risk(clause_type: str, extracted_text: str, confidence: float) -> Tuple[float, str, str]:
        """
        Assess risk for a specific clause
        
        Args:
            clause_type: Type of clause
            extracted_text: Extracted clause text (or None if not found)
            confidence: Model confidence score
        
        Returns:
            Tuple of (risk_score, risk_level, reliability_flag)
        """
        # If clause not found
        if not extracted_text or extracted_text.strip() == "":
            return RiskRules._assess_missing_clause(clause_type)
        
        # Assess based on clause type and content
        base_risk = RiskRules._calculate_base_risk(clause_type, extracted_text)
        importance = RiskRules.IMPORTANCE_WEIGHTS.get(clause_type, 0.5)
        
        # Final risk score (do NOT multiply by confidence to avoid underestimation)
        final_risk = base_risk * importance
        
        # Determine risk level
        if final_risk >= 60:
            risk_level = "HIGH"
        elif final_risk >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Reliability flag for low confidence on high-risk clauses
        reliability_flag = None
        if confidence < 0.6 and final_risk >= 60:
            reliability_flag = "REQUIRES_HUMAN_VERIFICATION"
        
        return round(final_risk, 2), risk_level, reliability_flag
    
    @staticmethod
    def _assess_missing_clause(clause_type: str) -> Tuple[float, str, str]:
        """Assess risk for missing clauses"""
        critical_clauses = ["Cap On Liability", "Termination For Convenience", "Governing Law"]
        
        if clause_type in critical_clauses:
            return 85.0, "HIGH", "MISSING_CRITICAL"
        else:
            return 0.0, "NOT_FOUND", None
    
    @staticmethod
    def _calculate_base_risk(clause_type: str, text: str) -> float:
        """Calculate base risk score based on clause content patterns"""
        text_lower = text.lower()
        
        # Indemnity clause rules
        if clause_type == "Indemnity":
            if any(word in text_lower for word in ["unlimited", "uncapped", "all claims", "any and all"]):
                return 90
            if "one-sided" in text_lower or "licensee shall indemnify" in text_lower:
                return 75
            if "mutual" in text_lower and any(word in text_lower for word in ["reasonable", "limited"]):
                return 30
            return 60
        
        # Liability cap rules
        if clause_type == "Cap On Liability":
            if any(word in text_lower for word in ["no cap", "unlimited", "uncapped"]):
                return 85
            if re.search(r'\$\s*\d{1,3}(,\d{3})*', text):  # Has dollar amount
                amount_match = re.search(r'\$\s*(\d{1,3}(,\d{3})*)', text)
                if amount_match:
                    amount = int(amount_match.group(1).replace(',', ''))
                    if amount < 100000:
                        return 60
                    elif amount < 1000000:
                        return 40
                    else:
                        return 25
            return 50
        
        # Uncapped liability
        if clause_type == "Uncapped Liability":
            return 90  # Always high risk if found
        
        # Termination rules
        if clause_type == "Termination For Convenience":
            if "no termination" in text_lower or "cannot terminate" in text_lower:
                return 80
            if re.search(r'(\d+)\s*days', text_lower):
                days_match = re.search(r'(\d+)\s*days', text_lower)
                days = int(days_match.group(1))
                if days > 180:
                    return 65
                elif days > 90:
                    return 50
                else:
                    return 25
            return 55
        
        # Auto-renewal rules
        if "Renewal" in clause_type:
            if "auto" in text_lower or "automatic" in text_lower:
                if "notice" in text_lower:
                    if re.search(r'(\d+)\s*days', text_lower):
                        days_match = re.search(r'(\d+)\s*days', text_lower)
                        days = int(days_match.group(1))
                        if days < 30:
                            return 70
                        elif days < 90:
                            return 55
                        else:
                            return 40
                return 70
            return 20
        
        # IP ownership rules
        if "IP Ownership" in clause_type:
            if any(word in text_lower for word in ["customer loses", "vendor owns all", "exclusive ownership"]):
                return 85
            if "unclear" in text_lower or "ambiguous" in text_lower:
                return 60
            if "customer retains" in text_lower or "licensee owns" in text_lower:
                return 20
            return 50
        
        # Non-compete rules
        if clause_type == "Non-Compete":
            if re.search(r'(\d+)\s*(year|years)', text_lower):
                years_match = re.search(r'(\d+)\s*(year|years)', text_lower)
                years = int(years_match.group(1))
                if years >= 5:
                    return 80
                elif years >= 3:
                    return 60
                elif years >= 1:
                    return 40
            return 50
        
        # Audit rights rules
        if clause_type == "Audit Rights":
            if "unlimited" in text_lower or "at any time" in text_lower:
                return 65
            if "no audit" in text_lower:
                return 55
            return 25
        
        # Governing law rules
        if clause_type == "Governing Law":
            unfavorable_jurisdictions = ["cayman", "bermuda", "offshore"]
            if any(jurisdiction in text_lower for jurisdiction in unfavorable_jurisdictions):
                return 50
            return 15
        
        # Default risk for other clauses
        return 40
    
    @staticmethod
    def calculate_overall_risk(clause_risks: Dict[str, Dict]) -> float:
        """
        Calculate overall contract risk score
        
        Args:
            clause_risks: Dictionary of clause type to risk info
        
        Returns:
            Overall risk score (0-100)
        """
        total_weighted_risk = 0
        total_weight = 0
        missing_critical_penalty = 0
        high_risk_count = 0
        
        for clause_type, risk_info in clause_risks.items():
            if risk_info["risk_level"] == "NOT_FOUND":
                if risk_info.get("reliability_flag") == "MISSING_CRITICAL":
                    missing_critical_penalty += 10
                continue
            
            weight = RiskRules.IMPORTANCE_WEIGHTS.get(clause_type, 0.5)
            total_weighted_risk += risk_info["risk_score"] * weight
            total_weight += weight
            
            if risk_info["risk_level"] == "HIGH":
                high_risk_count += 1
        
        # Calculate base score
        if total_weight > 0:
            base_score = total_weighted_risk / total_weight
        else:
            base_score = 50  # Default if no clauses found
        
        # Add penalties
        final_score = base_score + missing_critical_penalty
        
        # Additional penalty for multiple high-risk clauses
        if high_risk_count >= 3:
            final_score += 15
        
        return min(round(final_score, 2), 100)
