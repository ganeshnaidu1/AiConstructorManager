# AI Constructor Manager

A simplified construction bill verification and project management system.

## Project Structure

```
AiConstructorManager/
├── frontend/                 # Web interface
│   ├── index.html           # Main HTML file
│   ├── styles.css           # CSS styling
│   ├── app.js               # JavaScript application logic
│   └── package.json         # Frontend dependencies
├── backend/                 # FastAPI backend
│   └── app/
│       ├── main.py          # Core API endpoints
│       ├── di_client.py     # Azure Document Intelligence integration
│       ├── fraud_detector.py # Fraud detection logic
│       └── validation.py    # GSTIN and other validations
├── DB/                      # Database layer
│   └── Connection.py        # PostgreSQL connection and queries
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Quick Start

1. **Install Backend Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Backend Server**:
   ```bash
   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Start Frontend Server**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Access the Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Core Features

### Owner Dashboard
- Create projects with budgets
- View all projects and spending status
- Review and approve/reject bills
- Real-time budget tracking

### Site Engineer Interface
- Upload bill PDFs for processing
- Select project for bill assignment
- View upload status and recent submissions

### Fraud Detection
- Automatic arithmetic validation
- GSTIN verification
- Duplicate bill detection
- Risk scoring for each bill

## Technology Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: FastAPI, Python
- **Database**: PostgreSQL
- **Document Processing**: Azure Document Intelligence
- **Fraud Detection**: Custom algorithms + GSTIN validation

Quick start (macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```
