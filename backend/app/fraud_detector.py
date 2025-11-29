"""
Fraud Detection Module

Implements basic fraud detection for bills without heavy ML dependencies.
Uses heuristics and pattern matching.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta


class FraudDetector:
    """
    Basic fraud detection engine for construction bills.
    Checks for:
    - Duplicate bills
    - Amount anomalies
    - Line item validation
    - Vendor verification
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.fraud_reasons = []
        self.fraud_score = 0.0
    
    def detect_fraud(self, bill: Dict[str, Any], parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main fraud detection method.
        
        Args:
            bill: Bill data from database (with vendor_name, total_amount, etc)
            parsed_data: Extracted data from PDF
        
        Returns:
            {
                "fraud_score": 0-100,
                "is_suspicious": bool,
                "reasons": [list of reasons],
                "recommendation": "approve" | "review" | "reject"
            }
        """
        self.fraud_reasons = []
        self.fraud_score = 0.0
        
        bill_id = bill.get("bill_id")
        vendor = bill.get("vendor_name", "")
        amount = bill.get("total_amount", 0)
        
        # Check 1: Duplicate detection
        self._check_duplicate(bill_id, vendor, amount)
        
        # Check 2: Line item validation
        self._validate_line_items(parsed_data)
        
        # Check 3: Amount anomaly
        self._check_amount_anomaly(vendor, amount)
        
        # Check 4: Vendor risk
        self._check_vendor_risk(vendor)
        
        # Determine recommendation
        recommendation = self._get_recommendation()
        
        return {
            "fraud_score": round(self.fraud_score, 2),
            "is_suspicious": self.fraud_score > 40,
            "reasons": self.fraud_reasons,
            "recommendation": recommendation
        }
    
    def _check_duplicate(self, bill_id: str, vendor: str, amount: float):
        """Check if a similar bill was submitted recently."""
        if not self.db:
            return
        
        try:
            # Look for bills with same vendor and similar amount in last 7 days
            query = """
                SELECT bill_id, created_at FROM bills 
                WHERE vendor_name = %s 
                AND ABS(total_amount - %s) < (%s * 0.05)
                AND created_at > NOW() - INTERVAL '7 days'
                AND bill_id != %s
                LIMIT 5
            """
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (vendor, amount, amount, bill_id))
                similar_bills = cursor.fetchall()
            
            if similar_bills:
                self.fraud_score += 25
                dates = [str(b.get('created_at', '')) for b in similar_bills]
                self.fraud_reasons.append(f"Similar bill from {vendor} found in last 7 days")
        except Exception as e:
            print(f"Error checking duplicates: {e}")
    
    def _validate_line_items(self, parsed_data: Dict[str, Any]):
        """Validate line items: qty × rate = total."""
        line_items = parsed_data.get("line_items", [])
        
        if not line_items:
            return
        
        invalid_count = 0
        
        for idx, item in enumerate(line_items):
            qty = self._to_number(item.get("qty") or item.get("quantity"))
            rate = self._to_number(item.get("rate") or item.get("unit_price") or item.get("price"))
            total = self._to_number(item.get("total") or item.get("amount") or item.get("total_price"))
            
            if qty is not None and rate is not None and total is not None:
                expected = round(qty * rate, 2)
                diff = abs(expected - total)
                
                # If difference > 1, it's suspicious
                if diff > 1.0:
                    invalid_count += 1
        
        if invalid_count > 0:
            # Score increases based on how many line items are wrong
            self.fraud_score += min(30, 5 * invalid_count)
            self.fraud_reasons.append(f"{invalid_count} line item(s) with amount mismatch")
    
    def _check_amount_anomaly(self, vendor: str, amount: float):
        """Check if bill amount is unusual for this vendor."""
        if not self.db or amount <= 0:
            return
        
        try:
            # Get average bill amount for this vendor in last 30 days
            query = """
                SELECT 
                    AVG(total_amount) as avg_amount,
                    MAX(total_amount) as max_amount,
                    MIN(total_amount) as min_amount,
                    COUNT(*) as bill_count
                FROM bills
                WHERE vendor_name = %s
                AND created_at > NOW() - INTERVAL '30 days'
            """
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (vendor,))
                result = cursor.fetchone()
            
            if result and result.get('bill_count', 0) > 2:
                avg = self._to_number(result.get('avg_amount'))
                max_amt = self._to_number(result.get('max_amount'))
                
                if avg and avg > 0:
                    # If current amount is > 150% of average, it's suspicious
                    if amount > avg * 1.5:
                        deviation = ((amount - avg) / avg) * 100
                        self.fraud_score += min(20, 10 + (deviation / 50))
                        self.fraud_reasons.append(f"Amount {deviation:.0f}% above average for {vendor}")
        
        except Exception as e:
            print(f"Error checking amount anomaly: {e}")
    
    def _check_vendor_risk(self, vendor: str):
        """Check if vendor has history of issues."""
        if not self.db or not vendor:
            return
        
        try:
            # Count rejected bills from this vendor
            query = """
                SELECT COUNT(*) as rejected_count
                FROM bills
                WHERE vendor_name = %s
                AND status = 'rejected'
            """
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (vendor,))
                result = cursor.fetchone()
            
            rejected = result.get('rejected_count', 0) if result else 0
            
            if rejected > 2:
                self.fraud_score += min(15, 5 + (rejected * 2))
                self.fraud_reasons.append(f"Vendor has {rejected} rejected bills")
        
        except Exception as e:
            print(f"Error checking vendor risk: {e}")
    
    def _to_number(self, value) -> float:
        """Convert value to float."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace(",", ""))
        except:
            return None
    
    def _get_recommendation(self) -> str:
        """Get recommendation based on fraud score."""
        if self.fraud_score < 20:
            return "approve"
        elif self.fraud_score < 50:
            return "review"
        else:
            return "reject"


def detect_bill_fraud(bill: Dict[str, Any], parsed_data: Dict[str, Any], db_connection=None) -> Dict[str, Any]:
    """Utility function to detect fraud."""
    detector = FraudDetector(db_connection)
    return detector.detect_fraud(bill, parsed_data)
