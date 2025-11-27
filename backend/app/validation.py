"""Validation helpers: OCR extraction and GSTIN validation.

Requirements (local prototype):
- install poppler (macOS: `brew install poppler`)
- `pip install pytesseract pdf2image Pillow`

This module provides:
- ocr_extract_text_from_pdf(pdf_path) -> str
- find_multiplications_in_text(text) -> dict
- validate_gstin(gstin) -> dict
"""
from pathlib import Path
import re
from typing import List, Dict, Any

try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
except Exception:
    # If OCR deps not installed, functions will raise helpful errors at runtime
    convert_from_path = None
    pytesseract = None


def ocr_extract_text_from_pdf(pdf_path: str, dpi: int = 200) -> str:
    """Extract text from a PDF using pdf2image + pytesseract.

    Returns the concatenated text of all pages.
    """
    if convert_from_path is None or pytesseract is None:
        raise RuntimeError("OCR dependencies not available. Install pdf2image and pytesseract.")

    pages = convert_from_path(pdf_path, dpi=dpi)
    texts: List[str] = []
    for page in pages:
        text = pytesseract.image_to_string(page)
        texts.append(text)
    return "\n".join(texts)


def find_multiplications_in_text(text: str, tolerance: float = 1.0) -> Dict[str, Any]:
    """Search OCR text for multiplication patterns and verify results.

    Strategy:
    - Find explicit patterns like `200 x 385 = 77000` (various separators)
    - Also scan runs of 3 numbers and check if first*second ~= third

    Returns dict with found_matches and summary pass/fail.
    """
    results: List[Dict[str, Any]] = []

    # pattern: qty x rate = total  (allow x, X, *, × and = or :)
    pat = re.compile(r"(\d+[\.,]?\d*)\s*[xX\*×]\s*(\d+[\.,]?\d*)\s*[=:\-]\s*(\d+[\.,]?\d*)")
    for m in pat.finditer(text):
        a = float(m.group(1).replace(",", ""))
        b = float(m.group(2).replace(",", ""))
        c = float(m.group(3).replace(",", ""))
        prod = a * b
        ok = abs(prod - c) <= tolerance
        results.append({"qty": a, "rate": b, "total": c, "computed": prod, "ok": ok, "match_text": m.group(0)})

    # fallback: look for sequences of three numbers within a short window
    nums = [float(n.replace(",", "")) for n in re.findall(r"(\d+[\.,]?\d*)", text)]
    # scan triples
    for i in range(len(nums) - 2):
        a, b, c = nums[i], nums[i + 1], nums[i + 2]
        prod = a * b
        if abs(prod - c) <= tolerance:
            results.append({"qty": a, "rate": b, "total": c, "computed": prod, "ok": True, "match_text": f"{a} * {b} ~= {c}"})

    summary = {"total_matches": len(results), "all_ok": all(r.get("ok") for r in results) if results else False}
    return {"matches": results, "summary": summary}


def validate_gstin(gstin: str) -> Dict[str, Any]:
    """Validate GSTIN format for Indian GST numbers.

    This function checks:
    - length == 15
    - pattern: 2 digits (state) + 10-char PAN-like + 1 entity char + 'Z' + checksum char
    - state code between 01 and 37 (basic sanity)

    Note: A full checksum validation is not implemented here — this checks format and simple rules.
    """
    gst = (gstin or "").strip().upper()
    result = {"gstin": gst, "valid_format": False, "state_code_ok": False, "notes": []}

    if len(gst) != 15:
        result["notes"].append("GSTIN must be 15 characters long")
        return result

    # regex for rough PAN-like middle: 5 letters, 4 digits, 1 letter
    import re

    pattern = re.compile(r"^(?P<state>\d{2})(?P<pan>[A-Z]{5}\d{4}[A-Z])(?P<entity>[A-Z0-9])Z(?P<checksum>[A-Z0-9])$")
    m = pattern.match(gst)
    if not m:
        result["notes"].append("GSTIN does not match expected pattern (state+PAN+entity+Z+checksum)")
        return result

    result["valid_format"] = True
    state = int(m.group("state"))
    if 1 <= state <= 37:
        result["state_code_ok"] = True
    else:
        result["notes"].append(f"State code {state} out of expected range 01-37")

    # We could implement checksum validation here; for now we note it's unchecked.
    result["notes"].append("checksum_not_validated")
    return result
