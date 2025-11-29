import os
from dotenv import load_dotenv
load_dotenv()
from typing import Any, Dict
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient


def _get_client():
    endpoint = os.getenv("document_intelligence_endpoint")
    key = os.getenv("document_intelligence_key")
    if not endpoint or not key:
        raise RuntimeError("FORM_RECOGNIZER_ENDPOINT and FORM_RECOGNIZER_KEY must be set in env")
    return DocumentAnalysisClient(endpoint, AzureKeyCredential(key))


def analyze_invoice(pdf_path: str) -> Dict[str, Any]:
    """Analyze an invoice PDF using Azure Document Intelligence (prebuilt invoice).

    Returns a normalized dict with keys: vendor, invoice_date, invoice_id, line_items, taxes, total_amount, raw
    """
    client = _get_client()
    with open(pdf_path, "rb") as fd:
        poller = client.begin_analyze_document("prebuilt-invoice", fd)
        result = poller.result()

    # provide raw result for auditability
    raw = result.to_dict()

    parsed: Dict[str, Any] = {"raw": raw}

    try:
        if hasattr(result, "documents") and result.documents:
            doc = result.documents[0]
            fields = doc.fields
            # simple mappings (field names may vary)
            def safe(field_name):
                f = fields.get(field_name)
                return f.value if f is not None else None

            parsed["vendor"] = safe("VendorName") or safe("Vendor") or safe("SellerName")
            parsed["invoice_id"] = safe("InvoiceId") or safe("InvoiceNumber")
            parsed["invoice_date"] = safe("InvoiceDate")
            parsed["total_amount"] = safe("InvoiceTotal") or safe("AmountDue")
            parsed["taxes"] = safe("TotalTax")
            
            # Extract GSTIN and tax information
            parsed["vendor_gstin"] = safe("VendorTaxId") or safe("SellerTaxId") or safe("GSTIN")
            parsed["customer_gstin"] = safe("CustomerTaxId") or safe("BuyerTaxId")
            parsed["tax_details"] = safe("TaxDetails")
            
            # Try to extract GSTIN from vendor address or additional fields
            vendor_addr = safe("VendorAddress") or safe("SellerAddress")
            if vendor_addr and not parsed["vendor_gstin"]:
                # Try to extract GSTIN pattern from address string
                gstin_pattern = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}'
                if isinstance(vendor_addr, str):
                    import re
                    gstin_match = re.search(gstin_pattern, vendor_addr.replace(" ", ""))
                    if gstin_match:
                        parsed["vendor_gstin"] = gstin_match.group()
            
            # Also try to find GSTIN in any field that might contain it
            if not parsed["vendor_gstin"]:
                for field_name, field_obj in fields.items():
                    if field_obj and field_obj.value:
                        field_value = str(field_obj.value)
                        if any(keyword in field_name.lower() for keyword in ['gstin', 'gst', 'tax']):
                            import re
                            gstin_pattern = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}'
                            gstin_match = re.search(gstin_pattern, field_value.replace(" ", ""))
                            if gstin_match:
                                parsed["vendor_gstin"] = gstin_match.group()
                                break

            # items: try to extract table
            items = []
            items_field = fields.get("Items") or fields.get("InvoiceItems")
            if items_field is not None and items_field.value:
                # items_field.value is typically a list of dictionaries
                for row in items_field.value:
                    # each row may have keys: Description, Quantity, UnitPrice, Amount
                    desc = row.get("Description") or row.get("Item") or row.get("Name")
                    qty = row.get("Quantity")
                    unit = row.get("UnitPrice") or row.get("Price")
                    amt = row.get("Amount") or row.get("TotalPrice")
                    # values may be nested objects with 'value'
                    def val(x):
                        if x is None:
                            return None
                        if isinstance(x, dict) and "value" in x:
                            return x["value"]
                        return x

                    items.append({
                        "item": val(desc),
                        "qty": val(qty),
                        "rate": val(unit),
                        "total": val(amt),
                    })

            parsed["line_items"] = items
    except Exception:
        # If any mapping fails, return raw under parsed['raw'] and let caller decide
        parsed.setdefault("line_items", [])

    return parsed
