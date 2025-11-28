import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random

st.set_page_config(page_title="Construction Site Manager", layout="wide")

# Initialize session state for storing reports
if "reports" not in st.session_state:
    st.session_state.reports = []

# Sidebar for navigation
st.sidebar.title("Navigation")
user_role = st.sidebar.radio("Select Role", ["Site Officer", "Owner"])

# ============================================================================
# SITE OFFICER PAGE - Submit bills and labor count
# ============================================================================
if user_role == "Site Officer":
    st.title("📋 Site Officer - Daily Report")
    
    with st.form("daily_report_form"):
        st.subheader("Submit Daily Report")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_date = st.date_input("Report Date", datetime.now())
            report_type = st.radio("Report Type", ["Bill Submission", "Labor Count"])
        
        with col2:
            site_name = st.text_input("Site Name", "Main Construction Site")
            labor_count = st.number_input("Number of Workers", min_value=0, max_value=500, value=10, step=1)
        
        if report_type == "Bill Submission":
            st.subheader("Bill Details")
            col1, col2 = st.columns(2)
            with col1:
                bill_vendor = st.text_input("Vendor Name", "ABC Supplies")
                bill_amount = st.number_input("Bill Amount (₹)", min_value=0, value=5000, step=100)
            with col2:
                bill_category = st.selectbox("Category", ["Materials", "Labor", "Equipment", "Services"])
                bill_description = st.text_area("Bill Description", "Daily materials purchased")
        else:
            bill_vendor = None
            bill_amount = None
            bill_category = None
            bill_description = None
        
        additional_notes = st.text_area("Additional Notes", "")
        
        submitted = st.form_submit_button("Submit Report", use_container_width=True)
        
        if submitted:
            # Create report object
            report = {
                "date": str(report_date),
                "site_name": site_name,
                "type": report_type,
                "labor_count": labor_count,
                "bill_vendor": bill_vendor,
                "bill_amount": bill_amount,
                "bill_category": bill_category,
                "bill_description": bill_description,
                "notes": additional_notes,
                "submitted_at": datetime.now().isoformat()
            }
            
            st.session_state.reports.append(report)
            st.success("✅ Report submitted successfully!")
            st.balloons()
    
    # Display submitted reports
    if st.session_state.reports:
        st.subheader("Your Submitted Reports")
        for i, report in enumerate(st.session_state.reports):
            with st.expander(f"Report {i+1} - {report['date']} ({report['type']})"):
                st.write(f"**Site:** {report['site_name']}")
                st.write(f"**Workers:** {report['labor_count']}")
                if report['type'] == "Bill Submission":
                    st.write(f"**Vendor:** {report['bill_vendor']}")
                    st.write(f"**Amount:** ₹{report['bill_amount']}")
                    st.write(f"**Category:** {report['bill_category']}")
                st.write(f"**Notes:** {report['notes']}")

# ============================================================================
# OWNER PAGE - View reports and analytics
# ============================================================================
else:  # Owner role
    st.title("📊 Owner Dashboard")
    
    # Hardcoded data for demonstration
    today = datetime.now().date()
    
    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👷 Workers Today", 47, "+5 from yesterday")
    
    with col2:
        st.metric("📷 Unique Faces (Drone)", 45, "High accuracy")
    
    with col3:
        st.metric("📋 Reports Quality", "92%", "✅ Good")
    
    with col4:
        st.metric("💰 Bills Submitted", 12, "Today")
    
    st.divider()
    
    # Report Quality Section
    st.subheader("📈 Report Quality Analysis")
    
    quality_data = {
        "Date": ["Nov 26", "Nov 27", "Nov 28"],
        "Quality Score (%)": [88, 90, 92],
        "Reports Submitted": [8, 10, 12],
        "Workers Counted": [42, 45, 47],
        "Drone Faces": [40, 43, 45]
    }
    
    quality_df = pd.DataFrame(quality_data)
    st.dataframe(quality_df, use_container_width=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Workers Count Trend")
        st.line_chart({
            "Workers": [35, 38, 42, 45, 47],
            "Expected": [40, 40, 40, 40, 40]
        })
    
    with col2:
        st.subheader("Unique Drone Detections")
        st.bar_chart({
            "Detected": [30, 35, 40, 43, 45],
            "Manual Count": [32, 36, 42, 45, 47]
        })
    
    st.divider()
    
    # Site Officer Submitted Reports
    st.subheader("👥 Site Officer Reports")
    
    # Hardcoded sample reports
    sample_reports = [
        {
            "date": (today - timedelta(days=2)).isoformat(),
            "site": "Main Site",
            "workers": 42,
            "drone_faces": 40,
            "quality": "Good",
            "bills": 8
        },
        {
            "date": (today - timedelta(days=1)).isoformat(),
            "site": "Main Site",
            "workers": 45,
            "drone_faces": 43,
            "quality": "Excellent",
            "bills": 10
        },
        {
            "date": today.isoformat(),
            "site": "Main Site",
            "workers": 47,
            "drone_faces": 45,
            "quality": "Excellent",
            "bills": 12
        }
    ]
    
    # Add submitted reports from session state
    for report in st.session_state.reports:
        sample_reports.append({
            "date": report["date"],
            "site": report["site_name"],
            "workers": report["labor_count"],
            "drone_faces": report["labor_count"] - random.randint(0, 3),
            "quality": "Good",
            "bills": 1 if report["type"] == "Bill Submission" else 0
        })
    
    reports_df = pd.DataFrame(sample_reports)
    st.dataframe(reports_df, use_container_width=True)
    
    st.divider()
    
    # Summary Statistics
    st.subheader("📊 Summary (Last 3 Days)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_workers = sum(r["workers"] for r in sample_reports[-3:]) / 3
        st.metric("Avg Workers", f"{int(avg_workers)}", "Last 3 days")
    
    with col2:
        avg_drone_accuracy = sum(r["drone_faces"] for r in sample_reports[-3:]) / sum(r["workers"] for r in sample_reports[-3:]) * 100
        st.metric("Drone Accuracy", f"{avg_drone_accuracy:.1f}%", "Detection rate")
    
    with col3:
        total_bills = sum(r["bills"] for r in sample_reports[-3:])
        st.metric("Total Bills", f"{total_bills}", "Last 3 days")
