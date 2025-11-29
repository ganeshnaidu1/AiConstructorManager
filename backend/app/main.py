"""
AI Constructor Manager - Core Backend API
Simplified version with only essential endpoints for project management and bill processing.
"""

import os
import uuid
import json
import hashlib
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys

# Import modules
from .di_client import analyze_invoice
from .fraud_detector import detect_bill_fraud

# Add parent directory to path for DB imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from DB.SQLiteConnection import db
from backend.app.fraud_detector import FraudDetector

load_dotenv()

# Initialize fraud detector
fraud_detector = FraudDetector()

# Directory setup
BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "backend" / "storage"
BILLS_DIR = STORAGE_DIR / "bills"
BILLS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="AI Constructor Manager",
    description="Construction bill verification and project management system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/test/gstin/{gstin}")
async def test_gstin_validation(gstin: str):
    """Test GSTIN validation endpoint."""
    # Create comprehensive mock parsed data with the GSTIN
    mock_parsed_data = {
        "vendor_gstin": gstin if gstin != "EMPTY" else "",
        "vendor": "Test Vendor",
        "total_amount": 1000.0,
        "invoice_id": "TEST001",
        "invoice_date": "2025-11-29",
        "line_items": [
            {"item": "Construction Material", "qty": 10, "rate": 100, "total": 1000}
        ],
        "taxes": 180.0
    }
    
    # Test with fraud detector
    bill_data = {
        "bill_id": "test-bill",
        "vendor_name": "Test Vendor",
        "total_amount": 1000.0,
        "tenant_id": "test",
        "project_id": "test"
    }
    
    fraud_result = fraud_detector.detect_fraud(bill_data, mock_parsed_data)
    
    return {
        "gstin": gstin,
        "gstin_format_valid": len(gstin) == 15 and gstin != "EMPTY",
        "azure_di_extracted": {
            "vendor_gstin": mock_parsed_data.get("vendor_gstin"),
            "vendor": mock_parsed_data.get("vendor"),
            "total_amount": mock_parsed_data.get("total_amount")
        },
        "fraud_analysis": {
            "fraud_score": fraud_result.get("fraud_score", 0.0),
            "fraud_reasons": fraud_result.get("explanation", ""),
            "recommendation": fraud_result.get("recommendation", "unknown")
        }
    }

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

@app.post("/project/create")
async def create_project(project_data: dict):
    """Create a new project with budget."""
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        project_id = project_data.get("project_id")
        project_name = project_data.get("project_name")
        total_budget = project_data.get("total_budget", 0)
        
        if not project_id or not project_name:
            raise HTTPException(status_code=400, detail="Project ID and name required")
        
        # Create budget entry for the project
        success = db.create_budget(
            project_id=project_id,
            total_amount=total_budget,
            materials=0,
            labor=0,
            equipment=0,
            contingency=0
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        return {
            "project_id": project_id,
            "project_name": project_name,
            "total_budget": total_budget,
            "status": "created"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/projects")
async def list_projects():
    """Get all projects with budget and spending info."""
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    b.project_id,
                    b.total_amount as total_budget,
                    COALESCE(SUM(CASE WHEN bills.status = 'approved' THEN bills.total_amount ELSE 0 END), 0) as spent,
                    COUNT(bills.bill_id) as total_bills,
                    COUNT(CASE WHEN bills.status IN ('uploaded', 'analysed') THEN 1 END) as pending_bills
                FROM budgets b
                LEFT JOIN bills ON b.project_id = bills.project_id
                GROUP BY b.project_id, b.total_amount
                ORDER BY b.project_id
            """)
            
            projects = []
            for row in cursor.fetchall():
                projects.append({
                    "id": row[0],
                    "name": row[0].replace('_', ' ').title(),
                    "total_budget": float(row[1]) if row[1] else 0,
                    "spent": float(row[2]) if row[2] else 0,
                    "total_bills": int(row[3]) if row[3] else 0,
                    "pending_bills": int(row[4]) if row[4] else 0
                })
        
        return {"projects": projects, "total": len(projects)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============================================================================
# BILL PROCESSING
# ============================================================================

@app.post("/upload_bill")
async def upload_bill(file: UploadFile = File(...), tenant: str = Query(...), project: str = Query(...)):
    """Upload and process a bill PDF."""
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    bill_id = str(uuid.uuid4())
    target_dir = BILLS_DIR / tenant / project
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{bill_id}.pdf"
    
    # Save uploaded file
    try:
        content = await file.read()
        
        # Check for duplicates based on content hash
        file_hash = hashlib.md5(content).hexdigest()
        
        # Check if this file hash already exists in the database
        duplicate_detected = False
        duplicate_bill_id = None
        if db:
            existing_bills = db.get_all_bills()
            for bill in existing_bills:
                if bill.get('file_hash') == file_hash and bill.get('project_id') == project:
                    duplicate_detected = True
                    duplicate_bill_id = bill.get('bill_id')
                    print(f"⚠️ Duplicate file detected! Original bill: {duplicate_bill_id}")
                    break
        
        with open(file_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise  # Re-raise HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Process with Azure Document Intelligence
    try:
        parsed = analyze_invoice(str(file_path))
    except Exception as e:
        parsed = {"bill_id": bill_id, "error": str(e)}
    
    # Save parsed data
    parsed_path = STORAGE_DIR / "parsed"
    parsed_path.mkdir(parents=True, exist_ok=True)
    with open(parsed_path / f"{bill_id}.json", "w") as f:
        json.dump(parsed, f, indent=2, default=str)
    
    # Extract key information
    vendor_name = parsed.get("vendor") or parsed.get("supplier") or "Unknown"
    if isinstance(vendor_name, dict):
        vendor_name = vendor_name.get("name") or vendor_name.get("vendor_name") or "Unknown"
    
    total_amount = 0.0
    try:
        amount_str = str(parsed.get("total_amount") or parsed.get("InvoiceTotal") or "0")
        total_amount = float(amount_str.replace(",", ""))
    except (ValueError, AttributeError):
        total_amount = 0.0
    
    # Run fraud detection
    bill_data = {
        "bill_id": bill_id,
        "vendor_name": vendor_name,
        "total_amount": total_amount,
        "tenant_id": tenant,
        "project_id": project,
        "is_duplicate": duplicate_detected,
        "duplicate_of": duplicate_bill_id
    }
    fraud_result = fraud_detector.detect_fraud(bill_data, parsed)
    fraud_score = fraud_result.get("fraud_score", 0.0)
    fraud_reasons = fraud_result.get("explanation", "")
    
    # Add duplicate detection to fraud score
    if duplicate_detected:
        fraud_score += 30.0  # Add 30 points for duplicate
        if fraud_reasons:
            fraud_reasons += f" | DUPLICATE: Same file already uploaded as Bill {duplicate_bill_id}"
        else:
            fraud_reasons = f"DUPLICATE: Same file already uploaded as Bill {duplicate_bill_id}"
    
    if db:
        # Store in database
        success = db.insert_bill(
            bill_id=bill_id,
            tenant_id=tenant,
            project_id=project,
            vendor_name=vendor_name,
            total_amount=total_amount,
            fraud_score=fraud_score,
            status="uploaded",
            file_hash=file_hash
        )
        
        # Store line items if available
        line_items = parsed.get("line_items") or []
        if line_items and success:
            db.insert_line_items(bill_id, line_items)
            
        # Update fraud score and reasons
        if success:
            db.update_bill_fraud_score(bill_id, fraud_score, fraud_reasons)
    
    return {
        "bill_id": bill_id,
        "status": "uploaded",
        "vendor": vendor_name,
        "amount": total_amount,
        "fraud_score": fraud_score,
        "fraud_reasons": fraud_reasons,
        "duplicate_detected": duplicate_detected,
        "tenant": tenant,
        "project": project
    }

@app.get("/bills/project/{project_id}")
async def get_project_bills(project_id: str):
    """Get all bills for a project."""
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        bills = db.get_bills_by_project(project_id)
        return {
            "project_id": project_id,
            "bills": bills or [],
            "total": len(bills) if bills else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/bills")
async def list_all_bills():
    """List all bills."""
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        bills = db.get_all_bills()
        return {
            "bills": bills or [],
            "total": len(bills) if bills else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/get_bill_result/{bill_id}")
async def get_bill_analysis(bill_id: str):
    """Get detailed analysis for a bill including fraud detection results."""
    
    # Get bill data from database
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    bill_data = db.get_bill(bill_id)
    if not bill_data:
        raise HTTPException(status_code=404, detail="Bill not found in database")
    
    # Get parsed data from file
    parsed_path = STORAGE_DIR / "parsed" / f"{bill_id}.json"
    if not parsed_path.exists():
        raise HTTPException(status_code=404, detail="Bill analysis not found")
    
    with open(parsed_path) as f:
        parsed = json.load(f)
    
    # Run fraud detection to get fresh validation results
    fraud_result = detect_bill_fraud(bill_data, parsed, db)
    
    return {
        "bill_id": bill_id,
        "vendor_name": bill_data.get("vendor_name"),
        "total_amount": bill_data.get("total_amount"),
        "fraud_score": fraud_result.get("fraud_score", 0),
        "fraud_explanation": "; ".join(fraud_result.get("reasons", [])),
        "is_suspicious": fraud_result.get("is_suspicious", False),
        "recommendation": fraud_result.get("recommendation", "review"),
        "validations": fraud_result.get("validations", {}),
        "status": bill_data.get("status", "unknown"),
        "project_id": bill_data.get("project_id"),
        "line_items": parsed.get("line_items", []),
        "parsed_data": parsed
    }

# ============================================================================
# BILL APPROVAL/REJECTION
# ============================================================================

@app.post("/bill/{bill_id}/approve")
async def approve_bill(bill_id: str, approval_data: dict = None):
    """Approve a bill and deduct from project budget."""
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        # Get bill details
        bill = db.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        # Update status to approved
        success = db.update_bill_status(bill_id, "approved")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to approve bill")
        
        return {
            "bill_id": bill_id,
            "status": "approved",
            "approved_at": datetime.now().isoformat(),
            "message": "Bill approved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/bill/{bill_id}/reject")
async def reject_bill(bill_id: str, rejection_data: dict = None):
    """Reject a bill."""
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        bill = db.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        success = db.update_bill_status(bill_id, "rejected")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reject bill")
        
        return {
            "bill_id": bill_id,
            "status": "rejected",
            "rejected_at": datetime.now().isoformat(),
            "message": "Bill rejected successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============================================================================
# PROJECT BUDGET STATUS
# ============================================================================

@app.get("/project/{project_id}/budget")
async def get_project_budget(project_id: str):
    """Get project budget and spending summary."""
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        budget = db.get_budget(project_id)
        spending = db.get_project_spending(project_id)
        
        if not budget:
            return {
                "project_id": project_id,
                "budget": None,
                "spending": spending or {}
            }
        
        return {
            "project_id": project_id,
            "budget": dict(budget) if hasattr(budget, 'keys') else budget,
            "spending": spending or {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)