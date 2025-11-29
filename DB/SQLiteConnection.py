import os
import sqlite3
from contextlib import contextmanager
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from pathlib import Path

load_dotenv()

class SQLiteDatabaseConnection:
    """
    SQLite database connection manager.
    Handles connection lifecycle and provides context manager support.
    """
    
    def __init__(self):
        """Initialize database connection."""
        self.db_path = self._get_db_path()
        self._init_database()
    
    def _get_db_path(self) -> str:
        """Get database path from environment or use default."""
        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("sqlite:///"):
            return db_url.replace("sqlite:///", "")
        else:
            # Default path
            return str(Path(__file__).parent.parent / "constructor_manager.db")
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create budgets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    project_id TEXT PRIMARY KEY,
                    total_amount REAL NOT NULL DEFAULT 0,
                    materials REAL DEFAULT 0,
                    labor REAL DEFAULT 0,
                    equipment REAL DEFAULT 0,
                    contingency REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create bills table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bills (
                    bill_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    vendor_name TEXT,
                    total_amount REAL DEFAULT 0,
                    fraud_score REAL DEFAULT 0,
                    status TEXT DEFAULT 'uploaded',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fraud_reasons TEXT DEFAULT '',
                    FOREIGN KEY (project_id) REFERENCES budgets (project_id)
                )
            """)
            
            # Create line_items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bill_line_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id TEXT NOT NULL,
                    item_name TEXT,
                    qty REAL,
                    rate REAL,
                    total REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bill_id) REFERENCES bills (bill_id)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager to get a connection.
        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bills")
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager to get a cursor from a connection.
        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM bills")
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                print(f"Cursor error: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a query and optionally fetch results.
        
        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)
            fetch: If True, returns results; if False, just executes
        
        Returns:
            List of dictionaries if fetch=True, None otherwise
        """
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows] if rows else []
                return None
        except sqlite3.Error as e:
            print(f"Query execution error: {e}")
            raise
    
    def insert_bill(self, bill_id: str, tenant_id: str, project_id: str,
                   vendor_name: str, total_amount: float, 
                   fraud_score: float, status: str = "uploaded") -> bool:
        """Insert a bill record into the database."""
        query = """
            INSERT INTO bills (bill_id, tenant_id, project_id, vendor_name, total_amount, fraud_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (bill_id, tenant_id, project_id, vendor_name, total_amount, fraud_score, status))
            return True
        except sqlite3.Error as e:
            print(f"Error inserting bill: {e}")
            return False
    
    def insert_line_items(self, bill_id: str, line_items: List[Dict[str, Any]]) -> bool:
        """Insert line items for a bill."""
        query = """
            INSERT INTO bill_line_items (bill_id, item_name, qty, rate, total)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self.get_cursor() as cursor:
                for item in line_items:
                    cursor.execute(query, (
                        bill_id,
                        item.get("item") or item.get("description"),
                        item.get("qty") or item.get("quantity"),
                        item.get("rate") or item.get("unit_price") or item.get("price"),
                        item.get("total") or item.get("amount") or item.get("total_price")
                    ))
            return True
        except sqlite3.Error as e:
            print(f"Error inserting line items: {e}")
            return False
    
    def get_bill(self, bill_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a bill by ID."""
        query = "SELECT * FROM bills WHERE bill_id = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (bill_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Error retrieving bill: {e}")
            return None
    
    def get_bills_by_project(self, project_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve all bills for a project."""
        query = "SELECT * FROM bills WHERE project_id = ? ORDER BY created_at DESC"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (project_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows] if rows else []
        except sqlite3.Error as e:
            print(f"Error retrieving bills for project: {e}")
            return None
    
    def get_all_bills(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieve all bills."""
        query = "SELECT * FROM bills ORDER BY created_at DESC"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows] if rows else []
        except sqlite3.Error as e:
            print(f"Error retrieving all bills: {e}")
            return []
    
    def update_bill_status(self, bill_id: str, status: str) -> bool:
        """Update the status of a bill."""
        query = "UPDATE bills SET status = ? WHERE bill_id = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (status, bill_id))
            return True
        except sqlite3.Error as e:
            print(f"Error updating bill status: {e}")
            return False
    
    def get_bills_by_status(self, status: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve bills filtered by status."""
        query = "SELECT * FROM bills WHERE status = ? ORDER BY created_at DESC"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (status,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows] if rows else []
        except sqlite3.Error as e:
            print(f"Error retrieving bills by status: {e}")
            return None
    
    def get_bills_by_vendor(self, vendor_name: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve bills filtered by vendor name."""
        query = "SELECT * FROM bills WHERE vendor_name LIKE ? ORDER BY created_at DESC"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (f"%{vendor_name}%",))
                rows = cursor.fetchall()
                return [dict(row) for row in rows] if rows else []
        except sqlite3.Error as e:
            print(f"Error retrieving bills by vendor: {e}")
            return None
    
    def get_bill_with_line_items(self, bill_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve bill with its line items."""
        try:
            bill = self.get_bill(bill_id)
            if not bill:
                return None
            
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM bill_line_items WHERE bill_id = ?", (bill_id,))
                rows = cursor.fetchall()
                line_items = [dict(row) for row in rows] if rows else []
            
            bill['line_items'] = line_items
            return bill
        except sqlite3.Error as e:
            print(f"Error retrieving bill with line items: {e}")
            return None
    
    def update_bill_fraud_score(self, bill_id: str, fraud_score: float, fraud_reasons: str = "") -> bool:
        """Update fraud score and reasons for a bill."""
        query = "UPDATE bills SET fraud_score = ?, fraud_reasons = ? WHERE bill_id = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (fraud_score, fraud_reasons, bill_id))
            return True
        except sqlite3.Error as e:
            print(f"Error updating fraud score: {e}")
            return False
    
    # ============================================================================
    # BUDGET MANAGEMENT METHODS
    # ============================================================================
    
    def create_budget(self, project_id: str, total_amount: float, 
                     materials: float = 0, labor: float = 0, 
                     equipment: float = 0, contingency: float = 0) -> bool:
        """Create a budget for a project."""
        query = """
            INSERT OR REPLACE INTO budgets (project_id, total_amount, materials, labor, equipment, contingency)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (project_id, total_amount, materials, labor, equipment, contingency))
            return True
        except sqlite3.Error as e:
            print(f"Error creating budget: {e}")
            return False
    
    def get_budget(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get budget for a project."""
        query = "SELECT * FROM budgets WHERE project_id = ?"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (project_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Error retrieving budget: {e}")
            return None
    
    def get_project_spending(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get spending breakdown for a project."""
        query = """
            SELECT 
                COUNT(*) as bill_count,
                COALESCE(SUM(total_amount), 0) as total_spent,
                COALESCE(MIN(total_amount), 0) as min_bill,
                COALESCE(MAX(total_amount), 0) as max_bill,
                COALESCE(AVG(total_amount), 0) as avg_bill,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count
            FROM bills
            WHERE project_id = ?
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (project_id,))
                row = cursor.fetchone()
                return dict(row) if row else {}
        except sqlite3.Error as e:
            print(f"Error retrieving spending: {e}")
            return None
    
    def get_spending_by_vendor(self, project_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get spending breakdown by vendor for a project."""
        query = """
            SELECT 
                vendor_name,
                COUNT(*) as bill_count,
                COALESCE(SUM(total_amount), 0) as total_spent,
                COALESCE(AVG(total_amount), 0) as avg_bill,
                COALESCE(MIN(total_amount), 0) as min_bill,
                COALESCE(MAX(total_amount), 0) as max_bill,
                COALESCE(AVG(fraud_score), 0) as avg_fraud_score
            FROM bills
            WHERE project_id = ?
            GROUP BY vendor_name
            ORDER BY total_spent DESC
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (project_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows] if rows else []
        except sqlite3.Error as e:
            print(f"Error retrieving vendor spending: {e}")
            return None
    
    def get_spending_by_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get spending breakdown by bill status for a project."""
        query = """
            SELECT 
                status,
                COUNT(*) as bill_count,
                COALESCE(SUM(total_amount), 0) as total_amount
            FROM bills
            WHERE project_id = ?
            GROUP BY status
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (project_id,))
                rows = cursor.fetchall()
                spending = {}
                for row in rows:
                    row_dict = dict(row)
                    spending[row_dict['status']] = {
                        'count': row_dict['bill_count'],
                        'amount': row_dict['total_amount']
                    }
                return spending
        except sqlite3.Error as e:
            print(f"Error retrieving spending by status: {e}")
            return None
    
    def get_high_fraud_bills(self, project_id: str, min_score: float = 50) -> Optional[List[Dict[str, Any]]]:
        """Get bills with high fraud score."""
        query = """
            SELECT * FROM bills 
            WHERE project_id = ? 
            AND fraud_score >= ?
            ORDER BY fraud_score DESC
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (project_id, min_score))
                rows = cursor.fetchall()
                return [dict(row) for row in rows] if rows else []
        except sqlite3.Error as e:
            print(f"Error retrieving high fraud bills: {e}")
            return None
    
    def close(self):
        """Close database connection (SQLite auto-closes, so this is a no-op)."""
        pass


# Initialize global database instance
try:
    db = SQLiteDatabaseConnection()
    print("✅ SQLite database connection initialized successfully")
except Exception as e:
    print(f"Failed to initialize SQLite database connection: {e}")
    db = None