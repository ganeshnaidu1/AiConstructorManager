-- PostgreSQL schema for bills

CREATE TABLE IF NOT EXISTS bills (
  bill_id UUID PRIMARY KEY,
  tenant_id TEXT,
  project_id TEXT,
  vendor_name TEXT,
  total_amount NUMERIC,
  status TEXT,
  fraud_score NUMERIC,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bill_line_items (
  item_id SERIAL PRIMARY KEY,
  bill_id UUID REFERENCES bills(bill_id),
  item_name TEXT,
  qty NUMERIC,
  rate NUMERIC,
  total NUMERIC
);

CREATE TABLE IF NOT EXISTS mcp_cache_material_prices (
  id SERIAL PRIMARY KEY,
  material TEXT,
  date DATE,
  avg_price NUMERIC
);

CREATE TABLE IF NOT EXISTS mcp_vendor_history (
  id SERIAL PRIMARY KEY,
  vendor_name TEXT,
  data JSONB,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  bill_id UUID,
  action TEXT,
  details JSONB,
  logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
