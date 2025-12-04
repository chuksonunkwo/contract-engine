import os
import io
from typing import Optional, Tuple, Dict, List

import streamlit as st
import pandas as pd
import requests
from pypdf import PdfReader
from docx import Document

from engine import analyze_contract, AnalysisResult


# ---------------------------------------------------------
# Gumroad license verification
# ---------------------------------------------------------
GUMROAD_PRODUCT_ID = os.getenv("GUMROAD_PRODUCT_ID")  # preferred
GUMROAD_PRODUCT_PERMALINK = os.getenv("GUMROAD_PRODUCT_PERMALINK")  # fallback


def gumroad_license_enforced() -> bool:
    return bool(GUMROAD_PRODUCT_ID or GUMROAD_PRODUCT_PERMALINK)


def verify_license(license_key: str) -> Tuple[bool, str, Dict]:
    """
    Verify a Gumroad license key.

    If GUMROAD_PRODUCT_ID or GUMROAD_PRODUCT_PERMALINK is NOT configured,
    this function returns (True, dev-message, {}) so you can test locally.
    """
    license_key = (license_key or "").strip()

    if not gumroad_license_enforced():
        return (
            True,
            "License check is in development mode (no Gumroad product configured).",
            {},
        )

    if not license_key:
        return False, "Please enter a license key.", {}

    payload: Dict[str, str] = {
        "license_key": license_key,
        "increment_uses_count": "true",
    }

    if GUMROAD_PRODUCT_ID:
        payload["product_id"] = GUMROAD_PRODUCT_ID
    else:
        payload["product_permalink"] = GUMROAD_PRODUCT_PERMALINK

    try:
        resp = requests.post(
            "https://api.gumroad.com/v2/licenses/verify",
            data=payload,
            timeout=10,
        )
        data = resp.json()
    except Exception as e:
        return False, f"Error contacting license server: {e}", {}

    if not data.get("success"):
        return False, data.get("message", "License verification failed."), data

    purchase = data.get("purchase", {}) or {}

    if purchase.get("refunded") or purchase.get("chargebacked") or purchase.get(
        "disputed"
    ):
        return False, "This license has been refunded or chargebacked.", data

    if purchase.get("subscription_cancelled") or purchase.get(
        "subscription_ended"
    ):
        return False, "This subscription has been cancelled or ended.", data

    return True, "License verified successfully.", data


# ---------------------------------------------------------
# Simple check for API key
# ---------------------------------------------------------
def ensure_api_key() -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error(
            "OPENAI_API_KEY is not set.\n\n"
            "Locally, set it before running Streamlit, e.g. in PowerShell:\n"
            "$env:OPENAI_API_KEY = 'your_key_here'\n\n"
            "On Render, set it in the Environment Variables panel."
        )
        return None
    return api_key


# ---------------------------------------------------------
# File text extraction helpers
# ---------------------------------------------------------
def extract_text_from_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    text_chunks: List[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text:
            text_chunks.append(page_text)
    return "\n\n".join(text_chunks)


def extract_text_from_docx(uploaded_file) -> str:
    doc = Document(uploaded_file)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text_from_txt(uploaded_file) -> str:
    raw_bytes = uploaded_file.read()
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="ignore")


def handle_file_upload() -> Tuple[Optional[str], Optional[str]]:
    uploaded_file = st.file_uploader(
        "Upload contract file (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        help="For large files, analysis may take longer.",
    )

    if not uploaded_file:
        return None, None

    filename = uploaded_file.name.lower()
    try:
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(uploaded_file)
            status = f"Extracted text from PDF file: {uploaded_file.name}"
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(uploaded_file)
            status = f"Extracted text from DOCX file: {uploaded_file.name}"
        elif filename.endswith(".txt"):
            text = extract_text_from_txt(uploaded_file)
            status = f"Read text from TXT file: {uploaded_file.name}"
        else:
            st.error("Unsupported file type.")
            return None, None

        if not text.strip():
            st.warning("No readable text was extracted from the file.")
            return None, status

        return text, status

    except Exception as e:
        st.error(f"Error while extracting text from file: {e}")
        return None, None


# ---------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------
def inject_css():
    st.markdown(
        """
<style>
.report-container {
    max-width: 1200px;
    margin-left: auto;
    margin-right: auto;
}
.ce-card {
    background-color: #f8fafc;
    border-radius: 20px;
    padding: 20px 22px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.03);
}
.ce-card-hero {
    background: linear-gradient(135deg, #f973160f, #f9731605);
}
.ce-pill {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.ce-pill-risk-high {
    background-color: #fee2e2;
    color: #b91c1c;
}
.ce-pill-risk-medium {
    background-color: #fef3c7;
    color: #92400e;
}
.ce-pill-risk-low {
    background-color: #dcfce7;
    color: #166534;
}
.ce-pill-risk-unknown {
    background-color: #e5e7eb;
    color: #4b5563;
}
.ce-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94a3b8;
    margin-bottom: 6px;
}
.ce-risk-title {
    font-size: 2.4rem;
    font-weight: 800;
    margin-bottom: 4px;
    color: #b45309;
}
.ce-metric-title {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94a3b8;
    margin-bottom: 8px;
}
.ce-metric-value {
    font-size: 1rem;
    font-weight: 600;
    color: #0f172a;
}
.ce-section-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 8px;
}
.ce-section-caption {
    font-size: 0.85rem;
    color: #64748b;
}
.ce-risk-card {
    border-left-width: 4px;
    border-left-style: solid;
}
.ce-risk-border-high {
    border-left-color: #ef4444;
}
.ce-risk-border-medium {
    border-left-color: #f59e0b;
}
.ce-risk-border-low {
    border-left-color: #22c55e;
}
.ce-risk-border-unknown {
    border-left-color: #9ca3af;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.set_page_config(
        page_title="Contract Engine",
        page_icon="📑",
        layout="wide",
    )
    # Safely get license owner from session state
    license_owner = None
    if "license_owner" in st.session_state:
        license_owner = st.session_state.license_owner

    html = (
        "<div style='margin-bottom:4px;'>"
        "<span style='font-size:40px;font-weight:700;'>📑 Contract Engine</span>"
        "</div>"
    )
    if license_owner:
        html += (
            f"<div style='font-size:12px;color:#6b7280;'>"
            f"Licensed to: {license_owner}"
            f"</div>"
        )

    st.markdown(html, unsafe_allow_html=True)


def init_session_state():
    if "license_valid" not in st.session_state:
        st.session_state.license_valid = False
        st.session_state.license_message = "License not validated."
        st.session_state.license_key = ""
        st.session_state.license_owner = None


def render_sidebar() -> Dict:
    init_session_state()

    # License section
    st.sidebar.header("License")

    license_key_input = st.sidebar.text_input(
        "Gumroad license key",
        value=st.session_state.license_key,
        type="password",
        help="Paste the license key from your Gumroad receipt.",
    )

    if st.sidebar.button("Validate License"):
        ok, msg, meta = verify_license(license_key_input)
        st.session_state.license_valid = ok
        st.session_state.license_message = msg
        st.session_state.license_key = license_key_input

        # Extract customer email from Gumroad response when available
        owner_email = None
        if ok and meta:
            purchase = meta.get("purchase") or {}
            owner_email = purchase.get("email")
        st.session_state.license_owner = owner_email if owner_email else None

    if st.session_state.license_valid:
        st.sidebar.success(st.session_state.license_message)
    else:
        if gumroad_license_enforced():
            st.sidebar.warning(st.session_state.license_message)
        else:
            # Dev mode: softer hint only
            st.sidebar.caption(
                "License enforcement is disabled in this environment "
                "(no Gumroad product configured)."
            )

    st.sidebar.markdown("---")
    st.sidebar.header("Input Settings")

    party_role = st.sidebar.selectbox(
        "Your role in this contract",
        options=["buyer", "vendor"],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Input Mode")
    input_mode = st.sidebar.radio(
        "Choose how to provide the contract",
        options=["Paste text", "Upload file"],
        index=0,
    )

    st.sidebar.markdown("---")
    show_json = st.sidebar.checkbox(
        "Show raw JSON output (advanced)", value=False
    )

    run_button = st.sidebar.button("Run Analysis 💼")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Notes")
    st.sidebar.markdown(
        "- Paste contract text or upload a file (PDF/DOCX/TXT).\n"
        "- Output is structured for dashboards and reports.\n"
        "- Zero-Retention Policy – AI co-pilot, not a law firm. "
        "Results should be verified by a qualified attorney."
    )

    return {
        "party_role": party_role,
        "input_mode": input_mode,
        "run_button": run_button,
        "show_json": show_json,
    }


def render_input_area(input_mode: str) -> str:
    if input_mode == "Upload file":
        st.subheader("Contract File Upload")
        st.markdown(
            "Upload the contract file as **PDF**, **DOCX**, or **TXT**. "
            "Extracted text will be shown below for review."
        )

        extracted_text, status = handle_file_upload()

        if status:
            st.success(status)

        st.subheader("Extracted Contract Text (editable)")
        default_text = extracted_text or ""
        contract_text = st.text_area(
            label="Extracted contract text",
            value=default_text,
            height=350,
            placeholder=(
                "Once you upload a file, the extracted text will appear here. "
                "You can review and edit it before analysis."
            ),
        )
        return contract_text

    st.subheader("Contract Text (Paste)")
    st.markdown(
        "Paste the full contract text below. For very long contracts, you can start by "
        "testing with key sections (e.g., scope, liabilities, payment, termination)."
    )

    default_sample = (
        "This Agreement is made between Buyer and Contractor for the provision of "
        "maintenance and support services for offshore assets..."
    )

    contract_text = st.text_area(
        label="Contract body",
        value=default_sample,
        height=350,
        placeholder="Paste or type the full contract here...",
    )

    return contract_text


# ---------------------------------------------------------
# Dashboard-style cards
# ---------------------------------------------------------
def risk_border_class(risk_level: str) -> str:
    risk_level = (risk_level or "").lower()
    if risk_level == "high":
        return "ce-risk-border-high"
    if risk_level == "medium":
        return "ce-risk-border-medium"
    if risk_level == "low":
        return "ce-risk-border-low"
    return "ce-risk-border-unknown"


def risk_level_pill_class(risk_level: str) -> str:
    risk_level = (risk_level or "").lower()
    if risk_level == "high":
        return "ce-pill-risk-high"
    if risk_level == "medium":
        return "ce-pill-risk-medium"
    if risk_level == "low":
        return "ce-pill-risk-low"
    return "ce-pill-risk-unknown"


def render_top_summary(result: AnalysisResult):
    kc = result.keyCommercials
    summary_text = ""
    if result.executiveSummary:
        summary_text = result.executiveSummary[0].lstrip("- ").strip()

    col1, col2, col3, col4 = st.columns([2.2, 1.3, 1.3, 1.3])

    with col1:
        st.markdown(
            f"""
<div class="ce-card ce-card-hero">
  <div class="ce-label">Overall Risk Rating</div>
  <div class="ce-risk-title">{result.overallRisk}</div>
  <div style="font-size:0.85rem;color:#64748b;margin-bottom:10px;">
    High-level risk posture based on liability, HSE, payment, termination and legal exposure.
  </div>
  <div style="font-size:0.9rem;color:#0f172a;line-height:1.5;">
    {summary_text or "Executive risk summary will appear here based on the contract analysis."}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
<div class="ce-card">
  <div class="ce-metric-title">Value</div>
  <div class="ce-metric-value">{kc.value or "Not specified"}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
<div class="ce-card">
  <div class="ce-metric-title">Term</div>
  <div class="ce-metric-value">{kc.duration or "Not specified"}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
<div class="ce-card">
  <div class="ce-metric-title">Type</div>
  <div class="ce-metric-value">{kc.contractType or "Not specified"}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_strategic_risk_map(result: AnalysisResult):
    st.markdown("<div class='ce-section-title'>Strategic Risk Map</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='ce-section-caption'>Synthesis of key risk categories with business impact and mitigation levers.</div>",
        unsafe_allow_html=True,
    )

    if not result.riskMatrix:
        st.info("No risk matrix items generated.")
        return

    by_category: Dict[str, List] = {}
    for item in result.riskMatrix:
        by_category.setdefault(item.category, []).append(item)

    order = ["Liability", "Termination", "HSE", "Payment", "Legal"]
    ordered_items = []
    seen = set()
    for cat in order:
        if cat in by_category and by_category[cat]:
            ordered_items.append(by_category[cat][0])
            seen.add(cat)
    for cat, items in by_category.items():
        if cat not in seen:
            ordered_items.append(items[0])

    chunks = [ordered_items[i : i + 3] for i in range(0, len(ordered_items), 3)]

    for chunk in chunks:
        cols = st.columns(len(chunk))
        for col, item in zip(cols, chunk):
            border_class = risk_border_class(item.riskLevel)
            pill_class = risk_level_pill_class(item.riskLevel)
            description = item.description
            mitigation = item.mitigation or ""

            col.markdown(
                f"""
<div class="ce-card ce-risk-card {border_class}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div class="ce-label">{item.category.upper()}</div>
    <span class="ce-pill {pill_class}">{item.riskLevel.upper()} RISK</span>
  </div>
  <div style="font-size:0.9rem;color:#0f172a;margin-bottom:6px;">
    {description}
  </div>
  {"<div style='font-size:0.8rem;color:#64748b;'><strong>Mitigation focus:</strong> " + mitigation + "</div>" if mitigation else ""}
</div>
""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------
# Report builders (Markdown + DOCX)
# ---------------------------------------------------------
def build_markdown_report(result: AnalysisResult) -> str:
    kc = result.keyCommercials
    comp = result.compliance

    lines: List[str] = []

    lines.append("# Contract Analysis Report")
    lines.append("")
    lines.append(f"**Overall Risk:** {result.overallRisk}")
    lines.append("")
    lines.append("## Executive Summary")
    if result.executiveSummary:
        for bullet in result.executiveSummary:
            if bullet.strip().startswith("-"):
                lines.append(bullet)
            else:
                lines.append(f"- {bullet}")
    else:
        lines.append("- No executive summary provided.")
    lines.append("")

    lines.append("## Key Commercial Profile")
    lines.append(f"- **Value:** {kc.value or 'Not specified'}")
    lines.append(f"- **Duration / Term:** {kc.duration or 'Not specified'}")
    lines.append(f"- **Contract Type:** {kc.contractType or 'Not specified'}")
    lines.append(f"- **Pricing Model:** {kc.pricingModel or 'Not specified'}")
    if kc.renewalTerms:
        lines.append(f"- **Renewal Terms:** {kc.renewalTerms}")
    lines.append("")

    lines.append("## Compliance & Counterparty View")
    lines.append(f"- **Overall Compliance Risk:** {comp.overallComplianceRisk}")
    lines.append(f"- **Summary:** {comp.summary}")
    if comp.financialSignals:
        lines.append("- **Financial Signals:**")
        for s in comp.financialSignals:
            lines.append(f"  - {s}")
    if comp.sanctionsFlags:
        lines.append("- **Sanctions Flags:**")
        for s in comp.sanctionsFlags:
            lines.append(f"  - {s}")
    if comp.adverseMedia:
        lines.append("- **Adverse Media:**")
        for s in comp.adverseMedia:
            lines.append(f"  - {s}")
    lines.append("")

    lines.append("## Detailed McKinsey-Style Deep Dive")
    lines.append(result.detailedAnalysis or "_No detailed analysis provided._")

    return "\n".join(lines)


def build_docx_report(result: AnalysisResult) -> bytes:
    kc = result.keyCommercials
    comp = result.compliance

    doc = Document()

    doc.add_heading("Contract Analysis Report", level=1)
    doc.add_paragraph(f"Overall Risk: {result.overallRisk}")

    doc.add_heading("Executive Summary", level=2)
    if result.executiveSummary:
        for bullet in result.executiveSummary:
            doc.add_paragraph(bullet.lstrip("- ").strip(), style="List Bullet")
    else:
        doc.add_paragraph("No executive summary provided.")

    doc.add_heading("Key Commercial Profile", level=2)
    doc.add_paragraph(f"Value: {kc.value or 'Not specified'}")
    doc.add_paragraph(f"Duration / Term: {kc.duration or 'Not specified'}")
    doc.add_paragraph(f"Contract Type: {kc.contractType or 'Not specified'}")
    doc.add_paragraph(f"Pricing Model: {kc.pricingModel or 'Not specified'}")
    if kc.renewalTerms:
        doc.add_paragraph(f"Renewal Terms: {kc.renewalTerms}")

    doc.add_heading("Compliance & Counterparty View", level=2)
    doc.add_paragraph(f"Overall Compliance Risk: {comp.overallComplianceRisk}")
    doc.add_paragraph(f"Summary: {comp.summary}")
    if comp.financialSignals:
        doc.add_paragraph("Financial Signals:")
        for s in comp.financialSignals:
            doc.add_paragraph(s, style="List Bullet")
    if comp.sanctionsFlags:
        doc.add_paragraph("Sanctions Flags:")
        for s in comp.sanctionsFlags:
            doc.add_paragraph(s, style="List Bullet")
    if comp.adverseMedia:
        doc.add_paragraph("Adverse Media:")
        for s in comp.adverseMedia:
            doc.add_paragraph(s, style="List Bullet")

    doc.add_heading("Detailed McKinsey-Style Deep Dive", level=2)
    for line in (result.detailedAnalysis or "").splitlines():
        if not line.strip():
            doc.add_paragraph("")
        else:
            doc.add_paragraph(line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def render_download_section(result: AnalysisResult):
    st.markdown("### Export Report")
    md_report = build_markdown_report(result)
    docx_bytes = build_docx_report(result)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download Markdown Report",
            data=md_report.encode("utf-8"),
            file_name="contract_analysis_report.md",
            mime="text/markdown",
        )
    with col2:
        st.download_button(
            label="Download Word Report (.docx)",
            data=docx_bytes,
            file_name="contract_analysis_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


# ---------------------------------------------------------
# Main app
# ---------------------------------------------------------
def main():
    inject_css()
    render_header()
    api_key = ensure_api_key()
    settings = render_sidebar()
    contract_text = render_input_area(settings["input_mode"])

    if settings["run_button"]:
        if not api_key:
            st.stop()

        if not st.session_state.get("license_valid", False) and gumroad_license_enforced():
            st.error("Please enter and validate your Gumroad license key before running the analysis.")
            st.stop()

        if not contract_text.strip():
            st.error("Please provide contract text (paste or from upload) before running analysis.")
            st.stop()

        with st.spinner("Running analysis with Contract Engine…"):
            try:
                result: AnalysisResult = analyze_contract(
                    contract_text=contract_text,
                    party_role=settings["party_role"],
                    deal_context=None,
                )
            except Exception as e:
                st.error(f"Error during analysis: {e}")
                st.stop()

        st.markdown("<div class='report-container'>", unsafe_allow_html=True)

        render_top_summary(result)
        st.markdown("<br>", unsafe_allow_html=True)
        render_strategic_risk_map(result)
        st.markdown("<hr style='margin:32px 0;'>", unsafe_allow_html=True)

        st.markdown("### Executive Summary")
        if result.executiveSummary:
            for bullet in result.executiveSummary:
                if bullet.strip().startswith("-"):
                    st.markdown(bullet)
                else:
                    st.markdown(f"- {bullet}")
        else:
            st.info("No executive summary generated.")

        st.markdown("### Detailed McKinsey-Style Deep Dive")
        st.markdown(result.detailedAnalysis)

        if settings["show_json"]:
            st.markdown("---")
            st.subheader("Raw JSON Output")
            st.json(result.dict())

        st.markdown("---")
        render_download_section(result)

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
