import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def upload_bill(file, tenant="default", project="proj"):
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    params = {"tenant": tenant, "project": project}
    resp = requests.post(f"{BACKEND_URL}/upload_bill", files=files, params=params)
    resp.raise_for_status()
    return resp.json()


def get_bill_result(bill_id):
    resp = requests.get(f"{BACKEND_URL}/get_bill_result/{bill_id}")
    resp.raise_for_status()
    return resp.json()


def main():
    st.title("AI Construction Bill Verification - Prototype")
    st.write("Upload a bill PDF to parse and analyze fraud score.")

    tenant = st.text_input("Tenant ID", "default")
    project = st.text_input("Project ID", "proj")

    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Upload & Analyze"):
            with st.spinner("Uploading..."):
                try:
                    res = upload_bill(uploaded_file, tenant=tenant, project=project)
                    bill_id = res.get("bill_id")
                    st.success(f"Uploaded bill {bill_id}")
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                    return

            with st.spinner("Fetching result..."):
                try:
                    result = get_bill_result(bill_id)
                except Exception as e:
                    st.error(f"Failed to fetch result: {e}")
                    return

            st.subheader("Parsed Bill JSON")
            st.json(result.get("parsed"))

            st.subheader("Fraud Score")
            st.metric("fraud_score", result.get("fraud_score", 0.0))

            st.subheader("Explanation")
            st.write(result.get("fraud_explanation", "No explanation returned"))

            if st.button("Download parsed JSON"):
                st.download_button("Download JSON", data=str(result.get("parsed")), file_name=f"{bill_id}.json")


if __name__ == "__main__":
    main()
