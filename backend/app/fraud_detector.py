"""
Fraud Detection Module

Implements fraud detection for bills based on PDF content analysis:
1. Math validation: Sum of line items vs total amount
2. GSTIN validation: Check if vendor GSTIN is valid
3. Invoice integrity checks
"""

import re
import requests
from typing import Dict, Any, List, Tuple


class FraudDetector:
    """
    PDF-based fraud detection engine for construction bills.
    Focuses on document content validation:
    - Sum verification (line items vs total)
    - GSTIN validation 
    - Basic invoice integrity
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.fraud_reasons = []
        self.fraud_score = 0.0
    
    def detect_fraud(self, bill: Dict[str, Any], parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main fraud detection method focusing on PDF content.
        
        Args:
            bill: Bill data from database (with vendor_name, total_amount, etc)
            parsed_data: Extracted data from PDF by Azure Document Intelligence
        
        Returns:
            {
                "fraud_score": 0-100,
                "is_suspicious": bool,
                "reasons": [list of reasons],
                "recommendation": "approve" | "review" | "reject",
                "validations": {
                    "invoice_total": float,
                    "sum_of_line_totals": float,
                    "sum_ok": bool,
                    "gstin_validation": bool
                }
            }
        """
        self.fraud_reasons = []
        self.fraud_score = 0.0
        
        # Extract validation data
        validations = self._validate_invoice_math(parsed_data)
        gstin_valid = self._validate_gstin(parsed_data)
        validations["gstin_validation"] = gstin_valid
        
        # Check 1: Math validation (most important)
        if not validations["sum_ok"]:
            difference = abs(validations["invoice_total"] - validations["sum_of_line_totals"])
            if difference > 100:  # More than ₹100 difference
                self.fraud_score += 40
                self.fraud_reasons.append(f"Invoice total mismatch: ₹{difference:.2f} difference between total and sum of line items")
            elif difference > 10:  # More than ₹10 difference
                self.fraud_score += 20
                self.fraud_reasons.append(f"Minor invoice total mismatch: ₹{difference:.2f} difference")
        
        # Check 2: GSTIN validation
        if not gstin_valid:
            self.fraud_score += 15
            self.fraud_reasons.append("Invalid or missing GSTIN number")
        
        # Check 3: Missing critical information
        self._check_missing_info(parsed_data)
        
        # Check 4: Line item anomalies
        self._check_line_item_anomalies(parsed_data)
        
        # Determine recommendation
        recommendation = self._get_recommendation()
        
        return {
            "fraud_score": round(self.fraud_score, 2),
            "is_suspicious": self.fraud_score > 30,
            "reasons": self.fraud_reasons,
            "recommendation": recommendation,
            "validations": validations
        }
    
    def _validate_invoice_math(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that sum of line items equals invoice total.
        This is the core fraud detection check.
        """
        # Get invoice total
        invoice_total = self._extract_number(
            parsed_data.get("total_amount") or 
            parsed_data.get("InvoiceTotal") or 
            parsed_data.get("Amount") or 0
        )
        
        # Calculate sum of line items
        line_items = parsed_data.get("line_items", [])
        sum_of_line_totals = 0.0
        
        for item in line_items:
            item_total = self._extract_number(
                item.get("total") or 
                item.get("amount") or 
                item.get("Amount") or 
                item.get("TotalPrice") or 0
            )
            sum_of_line_totals += item_total
        
        # Check if they match (allow small rounding differences)
        difference = abs(invoice_total - sum_of_line_totals)
        sum_ok = difference <= 1.0  # Allow ₹1 difference for rounding
        
        return {
            "invoice_total": invoice_total,
            "sum_of_line_totals": sum_of_line_totals,
            "sum_ok": sum_ok,
            "difference": difference
        }
    
    def _validate_gstin(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Validate GSTIN number format and optionally check with government API.
        GSTIN format: 15 digits (2-state + 10-PAN + 1-entity + 1-Z + 1-check)
        """
        # Look for GSTIN in various possible fields
        gstin = None
        
        # Check common field names (prioritize Azure DI extracted fields)
        possible_fields = [
            "vendor_gstin", "customer_gstin",  # Azure Document Intelligence fields
            "gstin", "GSTIN", "gst_number", "GST", 
            "tax_id", "supplier_gstin", "VendorTaxId", "SellerTaxId"
        ]
        
        for field in possible_fields:
            if field in parsed_data and parsed_data[field]:
                gstin = str(parsed_data[field]).strip()
                break
        
        # If not found, try to extract from vendor info or raw text
        if not gstin:
            vendor_info = parsed_data.get("vendor", {})
            if isinstance(vendor_info, dict):
                for field in possible_fields:
                    if field in vendor_info:
                        gstin = str(vendor_info[field]).strip()
                        break
        
        if not gstin:
            return False  # No GSTIN found
        
        # Clean GSTIN (remove spaces, special chars)
        gstin = re.sub(r'[^A-Z0-9]', '', gstin.upper())
        
        # Basic format validation
        if len(gstin) != 15:
            return False
        
        # GSTIN pattern: 2 digits + 10 alphanumeric + 1 digit + 1 Z + 1 digit/letter
        pattern = r'^[0-9]{2}[A-Z0-9]{10}[0-9]{1}[Z]{1}[A-Z0-9]{1}$'
        if not re.match(pattern, gstin):
            return False
        
        # TODO: Add actual GSTIN verification API call here
        # For now, return True if format is correct
        
        # Optional: Call GSTIN verification API if available
        return self._verify_gstin_api(gstin)
    
    def _verify_gstin_api(self, gstin: str) -> bool:
        """Verify GSTIN with government API."""
        try:
            import os
            api_key = os.getenv("gstin_apikey")
            if not api_key:
                return True  # If no API key, assume format validation is sufficient
            
            # Mock API call for now - in production, use actual GSTIN verification API
            # Example: https://api.mastergst.com/gstinapi/v1.1/search/{gstin}
            
            # For demo purposes, consider some test GSTINs as valid
            valid_test_gstins = [
                "29AAFCD5862R000",  # Example valid GSTIN
                "09AAACF5862R1ZN",  # Another example
                "24GJSPS1279A1ZX",  # User test GSTIN
            ]
            
            if gstin in valid_test_gstins:
                return True
            
            # For actual implementation, uncomment below:
            # response = requests.get(f"https://api.gstin-verification.com/verify/{gstin}", 
            #                        headers={"Authorization": f"Bearer {api_key}"})
            # return response.status_code == 200 and response.json().get("valid", False)
            
            return True  # Default to valid if API not implemented
            
        except Exception as e:
            print(f"GSTIN API verification error: {e}")
            return True  # Default to valid on error
    
    def _check_missing_info(self, parsed_data: Dict[str, Any]):
        """Check for missing critical information."""
        required_fields = [
            ("vendor", "Vendor/Supplier name"),
            ("invoice_id", "Invoice number"),
            ("total_amount", "Total amount"),
        ]
        
        missing_count = 0
        for field, description in required_fields:
            if not parsed_data.get(field):
                missing_count += 1
        
        if missing_count > 0:
            self.fraud_score += missing_count * 5
            self.fraud_reasons.append(f"{missing_count} critical field(s) missing from invoice")
    
    def _check_line_item_anomalies(self, parsed_data: Dict[str, Any]):
        """Check individual line items for calculation errors."""
        line_items = parsed_data.get("line_items", [])
        
        if not line_items:
            self.fraud_score += 10
            self.fraud_reasons.append("No line items found in invoice")
            return
        
        calculation_errors = 0
        
        for idx, item in enumerate(line_items):
            qty = self._extract_number(item.get("qty") or item.get("quantity"))
            rate = self._extract_number(item.get("rate") or item.get("unit_price") or item.get("price"))
            total = self._extract_number(item.get("total") or item.get("amount"))
            
            # If we have all three values, check calculation
            if qty is not None and rate is not None and total is not None:
                expected = round(qty * rate, 2)
                actual = round(total, 2)
                
                if abs(expected - actual) > 0.5:  # Allow 50 paisa difference
                    calculation_errors += 1
        
        if calculation_errors > 0:
            self.fraud_score += min(25, calculation_errors * 8)
            self.fraud_reasons.append(f"{calculation_errors} line item(s) with calculation errors")
    
    def _extract_number(self, value) -> float:
        """Extract numeric value from various formats."""
        if value is None:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Handle string values
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[₹,$\s]', '', value)
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        
        # Handle dict format from Azure DI
        if isinstance(value, dict) and 'value' in value:
            return self._extract_number(value['value'])
        
        return 0.0
    
    def _get_recommendation(self) -> str:
        """Get recommendation based on fraud score."""
        if self.fraud_score < 15:
            return "approve"
        elif self.fraud_score < 40:
            return "review"
        else:
            return "reject"


def detect_bill_fraud(bill: Dict[str, Any], parsed_data: Dict[str, Any], db_connection=None) -> Dict[str, Any]:
    """Utility function to detect fraud in uploaded bill."""
    detector = FraudDetector(db_connection)
    return detector.detect_fraud(bill, parsed_data)
