// Configuration
const API_BASE = 'http://localhost:8000';

// State Management
let currentUser = 'owner'; // 'owner' or 'engineer'
let projects = [];
let bills = [];

// DOM Elements
const ownerTab = document.getElementById('ownerTab');
const engineerTab = document.getElementById('engineerTab');
const ownerView = document.getElementById('ownerView');
const engineerView = document.getElementById('engineerView');
const loadingOverlay = document.getElementById('loadingOverlay');

// Initialize App
document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    initializeOwnerView();
    initializeEngineerView();
    loadProjects();
});

// Navigation
function initializeNavigation() {
    ownerTab.addEventListener('click', () => switchView('owner'));
    engineerTab.addEventListener('click', () => switchView('engineer'));
}

function switchView(view) {
    currentUser = view;
    
    // Update navigation
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
    
    if (view === 'owner') {
        ownerTab.classList.add('active');
        ownerView.classList.add('active');
    } else {
        engineerTab.classList.add('active');
        engineerView.classList.add('active');
        loadProjectsForEngineer();
    }
}

// Owner View Functions
function initializeOwnerView() {
    const projectForm = document.getElementById('projectForm');
    const loadBillsBtn = document.getElementById('loadBills');
    
    projectForm.addEventListener('submit', handleProjectCreation);
    loadBillsBtn.addEventListener('click', loadBillsForProject);
}

async function handleProjectCreation(e) {
    e.preventDefault();
    
    const projectName = document.getElementById('projectName').value;
    const projectBudget = document.getElementById('projectBudget').value;
    
    if (!projectName || !projectBudget) {
        showAlert('Please fill all fields', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/project/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project_name: projectName,
                project_id: projectName.toLowerCase().replace(/\s+/g, '_'),
                total_budget: parseFloat(projectBudget),
                materials: 0,
                labor: 0,
                equipment: 0,
                contingency: 0
            })
        });
        
        if (response.ok) {
            showAlert('Project created successfully!', 'success');
            document.getElementById('projectForm').reset();
            loadProjects();
        } else {
            throw new Error('Failed to create project');
        }
    } catch (error) {
        showAlert('Error creating project: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function loadProjects() {
    try {
        const response = await fetch(`${API_BASE}/projects`);
        
        if (response.ok) {
            const data = await response.json();
            projects = data.projects || [];
        } else {
            projects = [];
        }
        
        updateProjectsList();
        updateProjectSelectors();
    } catch (error) {
        console.error('Error loading projects:', error);
        projects = [];
        updateProjectsList();
        updateProjectSelectors();
    }
}

function updateProjectsList() {
    const projectsList = document.getElementById('projectsList');
    
    if (projects.length === 0) {
        projectsList.innerHTML = '<p style="text-align: center; color: #666;">No projects yet. Create your first project!</p>';
        return;
    }
    
    projectsList.innerHTML = projects.map(project => `
        <div class="project-card">
            <div class="project-name">${project.name}</div>
            <div class="project-budget">Budget: ₹${project.total_budget.toLocaleString()}</div>
            <div class="budget-bar">
                <div class="budget-progress ${getBudgetStatus(project.spent, project.total_budget)}" 
                     style="width: ${Math.min((project.spent / project.total_budget) * 100, 100)}%"></div>
            </div>
            <small>Spent: ₹${project.spent.toLocaleString()} (${((project.spent / project.total_budget) * 100).toFixed(1)}%)</small>
            <div style="margin-top: 0.5rem; font-size: 0.9rem;">
                <span>📋 Bills: ${project.total_bills} | ⏳ Pending: ${project.pending_bills}</span>
            </div>
        </div>
    `).join('');
}

function getBudgetStatus(spent, total) {
    const percentage = (spent / total) * 100;
    if (percentage > 100) return 'danger';
    if (percentage > 80) return 'warning';
    return '';
}

function updateProjectSelectors() {
    const projectSelect = document.getElementById('projectSelect');
    const engineerProjectSelect = document.getElementById('engineerProjectSelect');
    
    const options = '<option value="">Select Project</option>' + 
        projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    
    projectSelect.innerHTML = options;
    engineerProjectSelect.innerHTML = options;
}

async function loadBillsForProject() {
    const projectId = document.getElementById('projectSelect').value;
    if (!projectId) {
        showAlert('Please select a project', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/bills/project/${projectId}`);
        
        if (response.ok) {
            const data = await response.json();
            bills = data.bills || [];
            updateBillsList();
        } else {
            throw new Error('Failed to load bills');
        }
    } catch (error) {
        showAlert('Error loading bills: ' + error.message, 'error');
        bills = [];
        updateBillsList();
    } finally {
        showLoading(false);
    }
}

function updateBillsList() {
    const billsList = document.getElementById('billsList');
    
    if (bills.length === 0) {
        billsList.innerHTML = '<p class="text-center">No bills found for this project.</p>';
        return;
    }
    
    // Filter for pending bills
    const pendingBills = bills.filter(bill => bill.status === 'uploaded' || bill.status === 'analysed');
    
    if (pendingBills.length === 0) {
        billsList.innerHTML = '<p class="text-center">No pending bills for review.</p>';
        return;
    }
    
    billsList.innerHTML = pendingBills.map(bill => `
        <div class="bill-item">
            <div class="bill-info">
                <div class="bill-detail">
                    <span class="bill-label">Bill ID</span>
                    <span class="bill-value">${bill.bill_id}</span>
                </div>
                <div class="bill-detail">
                    <span class="bill-label">Vendor</span>
                    <span class="bill-value">${bill.vendor_name || 'Unknown'}</span>
                </div>
                <div class="bill-detail">
                    <span class="bill-label">Amount</span>
                    <span class="bill-value">₹${(bill.total_amount || 0).toLocaleString()}</span>
                </div>
                <div class="bill-detail">
                    <span class="bill-label">Fraud Score</span>
                    <span class="fraud-score ${getFraudScoreClass(bill.fraud_score || 0)}">
                        ${(bill.fraud_score || 0).toFixed(1)}%
                    </span>
                </div>
                <div class="bill-detail">
                    <span class="bill-label">Status</span>
                    <span class="bill-value">${bill.status || 'Unknown'}</span>
                </div>
            </div>
            <div class="bill-actions">
                <button class="btn btn-success" onclick="approveBill('${bill.bill_id}', ${bill.total_amount || 0})">
                    ✅ Approve
                </button>
                <button class="btn btn-danger" onclick="rejectBill('${bill.bill_id}')">
                    ❌ Reject
                </button>
                <button class="btn btn-secondary" onclick="viewBillDetails('${bill.bill_id}')">
                    🔍 Details
                </button>
            </div>
        </div>
    `).join('');
}

function getFraudScoreClass(score) {
    if (score < 30) return 'fraud-low';
    if (score < 70) return 'fraud-medium';
    return 'fraud-high';
}

async function approveBill(billId, amount) {
    if (!confirm('Are you sure you want to approve this bill?')) return;
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/bill/${billId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                approved_by: 'owner',
                notes: 'Approved via web interface'
            })
        });
        
        if (response.ok) {
            showAlert('Bill approved successfully!', 'success');
            
            // Reload bills and projects to show updated budget
            await loadBillsForProject();
            await loadProjects();
        } else {
            throw new Error('Failed to approve bill');
        }
    } catch (error) {
        showAlert('Error approving bill: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function rejectBill(billId) {
    const reason = prompt('Please enter reason for rejection:');
    if (!reason) return;
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/bill/${billId}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                reason: reason,
                rejected_by: 'owner'
            })
        });
        
        if (response.ok) {
            showAlert('Bill rejected successfully!', 'success');
            await loadBillsForProject();
        } else {
            throw new Error('Failed to reject bill');
        }
    } catch (error) {
        showAlert('Error rejecting bill: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function viewBillDetails(billId) {
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/get_bill_result/${billId}`);
        
        if (response.ok) {
            const data = await response.json();
            showBillDetailsModal(data);
        } else {
            throw new Error('Failed to load bill details');
        }
    } catch (error) {
        showAlert('Error loading bill details: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function showBillDetailsModal(billData) {
    const details = `
Bill ID: ${billData.bill_id}
Fraud Score: ${billData.fraud_score}%
Fraud Explanation: ${billData.fraud_explanation}

Validations:
- Invoice Total: ₹${billData.validations?.invoice_total || 'N/A'}
- Sum of Lines: ₹${billData.validations?.sum_of_line_totals || 'N/A'}
- Sum Check: ${billData.validations?.sum_ok ? 'PASS' : 'FAIL'}

GSTIN Validation: ${billData.validations?.gstin_validation ? 'Checked' : 'Not Available'}
    `;
    
    alert(details);
}

// Engineer View Functions
function initializeEngineerView() {
    const billUploadForm = document.getElementById('billUploadForm');
    billUploadForm.addEventListener('submit', handleBillUpload);
}

async function loadProjectsForEngineer() {
    // Reuse the same projects loading logic
    await loadProjects();
}

async function handleBillUpload(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('engineerProjectSelect').value;
    const vendorName = document.getElementById('vendorName').value;
    const billFile = document.getElementById('billFile').files[0];
    
    if (!projectId || !vendorName || !billFile) {
        showAlert('Please fill all fields and select a file', 'error');
        return;
    }
    
    if (!billFile.name.toLowerCase().endsWith('.pdf')) {
        showAlert('Only PDF files are supported', 'error');
        return;
    }
    
    showLoading(true);
    
    const formData = new FormData();
    formData.append('file', billFile);
    
    try {
        const response = await fetch(`${API_BASE}/upload_bill?project=${projectId}&tenant=${vendorName}`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showUploadSuccess(result);
            document.getElementById('billUploadForm').reset();
            loadRecentUploads();
        } else {
            const errorText = await response.text();
            throw new Error(errorText);
        }
    } catch (error) {
        showUploadError(error.message);
    } finally {
        showLoading(false);
    }
}

function showUploadSuccess(result) {
    const uploadStatus = document.getElementById('uploadStatus');
    uploadStatus.className = 'upload-status success';
    
    let duplicateWarning = '';
    if (result.duplicate_detected) {
        duplicateWarning = `
        <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 0.5rem; margin: 0.5rem 0; border-radius: 5px; color: #856404;">
            ⚠️ <strong>Duplicate Detected:</strong> This file was already uploaded before!
        </div>`;
    }
    
    uploadStatus.innerHTML = `
        <h4>✅ Upload Successful!</h4>
        ${duplicateWarning}
        <p><strong>Bill ID:</strong> ${result.bill_id}</p>
        <p><strong>Vendor:</strong> ${result.vendor}</p>
        <p><strong>Amount:</strong> ₹${(result.amount || 0).toLocaleString()}</p>
        <p><strong>Fraud Score:</strong> ${(result.fraud_score || 0).toFixed(1)}%</p>
        <p><strong>Status:</strong> Uploaded successfully, pending owner review</p>
    `;
}

function showUploadError(error) {
    const uploadStatus = document.getElementById('uploadStatus');
    uploadStatus.className = 'upload-status error';
    uploadStatus.innerHTML = `
        <h4>❌ Upload Failed</h4>
        <p>${error}</p>
    `;
}

async function loadRecentUploads() {
    try {
        const response = await fetch(`${API_BASE}/bills`);
        
        if (response.ok) {
            const data = await response.json();
            const recentBills = (data.bills || []).slice(-5); // Show last 5 uploads
            updateRecentUploads(recentBills);
        }
    } catch (error) {
        console.error('Error loading recent uploads:', error);
    }
}

function updateRecentUploads(uploads) {
    const recentUploads = document.getElementById('recentUploads');
    
    if (uploads.length === 0) {
        recentUploads.innerHTML = '<p>No recent uploads</p>';
        return;
    }
    
    recentUploads.innerHTML = uploads.map(upload => `
        <div class="upload-item">
            <div class="upload-info">
                <h4>${upload.vendor_name || 'Unknown Vendor'}</h4>
                <p>Amount: ₹${(upload.total_amount || 0).toLocaleString()} | Fraud Score: ${(upload.fraud_score || 0).toFixed(1)}%</p>
                <small>Bill ID: ${upload.bill_id}</small>
            </div>
            <span class="upload-status-badge status-${upload.status || 'unknown'}">
                ${(upload.status || 'unknown').toUpperCase()}
            </span>
        </div>
    `).join('');
}

// Utility Functions
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.add('show');
    } else {
        overlay.classList.remove('show');
    }
}

function showAlert(message, type) {
    // Create a simple alert for now - you can enhance this with a proper modal
    const alertClass = type === 'success' ? 'success' : 'error';
    const alertDiv = document.createElement('div');
    alertDiv.className = `upload-status ${alertClass}`;
    alertDiv.innerHTML = message;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '10000';
    alertDiv.style.minWidth = '300px';
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        document.body.removeChild(alertDiv);
    }, 5000);
}

// Load recent uploads on engineer view
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(loadRecentUploads, 1000);
});
