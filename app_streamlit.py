# app_streamlit.py

import io
import os
from typing import Optional

import streamlit as st

from engine import AnalysisResult, analyze_contract, validate_license

# ===========================
# Basic page config & styles
# ===========================

st.set_page_config(
    page_title="Contract Engine – Oil & Gas Edition",
    layout="wide",
)

CUSTOM_CSS = """
<style>
/* Main title */
.contract-title {
    font-size: 40px;
    font-weight: 700;
    margin-bottom: 0.1rem;
}

/* Subheading under title */
.contract-subtitle {
    font-size: 13px;
    color: #6c757d;
    margin-bottom: 1.5rem;
}

/* Card styling for top summary tiles */
.ce-card {
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    border: 1px solid #e5e7eb;
    background: #ffffff;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

/* Risk level badges */
.badge-low {
    background-color: #ecfdf5;
    color: #166534;
    border-radius: 999px;
    padding: 0.1rem 0.6rem;
    font-size: 12px;
    font-weight: 600;
}
.badge-medium {
    background-color: #fffbeb;
    color: #92400e;
    border-radius: 999px;
    padding: 0.1rem 0.6rem;
    font-size: 12px;
    font-weight: 600;
}
.badge-high {
    background-color: #fef2f2;
    color: #b91c1c;
    border-radius: 999px;
    padding: 0.1rem 0.6rem;
    font-size: 12px;
    font-weight: 600;
}

/* Section titles */
.section-title {
    font-size: 22px;
    font-weight: 700;
    margin-top: 1.5rem;
}

/* Small muted label */
.label-muted {
    font-size: 12px;
    color: #6b7280;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ===========================
# Session helpers
# ===========================

if "license_ok" not in st.session_state:
    st.session_state.license_ok = False
    st.session_state.license_message = "Enter your Gumroad license key to unlock."
    st.session_state.last_key = ""

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
    st.session_state.analysis_error = None


# ===========================
# Utility: file text extraction
# ===========================

def _read_pdf(file) -> str:
    try:
        import pypdf  # type: ignore
    except Exception:
        try:
            import PyPDF2 as pypdf  # type: ignore
        except Exception:
            return "Unable to import PDF library. Please install 'pypdf' or 'PyPDF2'."

    reader = pypdf.PdfReader(file)
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n\n".join(pages)


def _read_docx(file) -> str:
    try:
        import docx  # python-docx  # type: ignore
    except Exception:
        return "Unable to import 'python-docx'. Please install it to read DOCX files."

    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_from_upload(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    suffix = (uploaded_file.name or "").lower()
    if suffix.endswith(".pdf"):
        return _read_pdf(uploaded_file)
    if suffix.endswith(".docx"):
        return _read_docx(uploaded_file)
    # Fallback – assume text
    try:
        return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


# ===========================
# Sidebar – license & inputs
# ===========================

with st.sidebar:
    st.markdown("#### License")
    license_key = st.text_input(
        "Gumroad license key",
        type="password",
        value=st.session_state.last_key,
    )
    if st.button("Validate License"):
        ok, msg = validate_license(license_key)
        st.session_state.license_ok = ok
        st.session_state.license_message = msg
        st.session_state.last_key = license_key

    # Status message
    if st.session_state.license_ok:
        st.success(st.session_state.license_message)
    else:
        st.warning(st.session_state.license_message)

    st.markdown("---")
    st.markdown("#### Input Settings")

    role = st.selectbox("Your role in this contract", ["buyer", "vendor"])

    st.markdown("#### Input Mode")
    input_mode = st.radio(
        "Choose how to provide the contract",
        ["Paste text", "Upload file"],
        index=0,
    )

    show_raw_json = st.checkbox(
        "Show raw JSON output (advanced)",
        value=False,
    )

    st.markdown("---")
    st.markdown("#### Notes")
    st.markdown(
        """
- Paste contract text or upload a file (PDF/DOCX/TXT).
- Output is structured for dashboards and reports.
- Zero-Retention Policy – AI co-pilot, not a law firm.
- Results should be verified by a qualified attorney.
        """,
        help="This tool provides commercial insight, not legal advice.",
    )

# ===========================
# Main layout – header
# ===========================

st.markdown(
    """
<div class="contract-title">Contract Engine</div>
<div class="contract-subtitle">
Licensed to: sales@jiculimited.com
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### Contract File Upload" if input_mode == "Upload file" else "### Contract Text (Paste)")

deal_context = ""  # reserved if you want to expose later in UI


# ===========================
# Contract input area
# ===========================

contract_text: Optional[str] = None

if input_mode == "Paste text":
    contract_text = st.text_area(
        "Contract body",
        height=260,
        placeholder=(
            "Paste the full contract text here. For very long contracts, "
            "you can start by testing key sections (scope, liabilities, payment, termination)."
        ),
    )
else:
    uploaded = st.file_uploader(
        "Upload contract file (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
    )
    if uploaded is not None:
        extracted = extract_text_from_upload(uploaded)
        st.success(f"Extracted text from file: {uploaded.name}")
        contract_text = st.text_area(
            "Extracted contract text (editable)",
            extracted,
            height=260,
        )
    else:
        contract_text = None

run_clicked = st.button("Run Analysis 🚀")

# ===========================
# Run analysis
# ===========================

if run_clicked:
    if not st.session_state.license_ok:
        st.error("Please validate a license key before running analysis.")
    elif not contract_text or not contract_text.strip():
        st.error("Please provide contract text (paste or upload a file).")
    else:
        with st.spinner("Running analysis with Contract Engine…"):
            try:
                result = analyze_contract(contract_text, role=role, deal_context=deal_context)
                st.session_state.analysis_result = result
                st.session_state.analysis_error = None
            except Exception as exc:  # noqa: BLE001
                st.session_state.analysis_result = None
                st.session_state.analysis_error = str(exc)

# ===========================
# Error display
# ===========================

if st.session_state.analysis_error:
    st.error("Error during analysis:")
    st.code(st.session_state.analysis_error, language="text")


# ===========================
# Visualisation helpers
# ===========================

def risk_badge(level: str) -> str:
    lvl = (level or "").lower()
    if lvl == "low":
        return '<span class="badge-low">LOW</span>'
    if lvl == "high":
        return '<span class="badge-high">HIGH</span>'
    return '<span class="badge-medium">MEDIUM</span>'


# ===========================
# Report export helper
# ===========================

def build_markdown_report(result: AnalysisResult, role: str, deal_context: str) -> str:
    kc = result.keyCommercials
    lines = []

    lines.append(f"# Contract Engine – Oil & Gas Edition\n")
    lines.append(f"Perspective: **{role.title()}**\n")
    if deal_context:
        lines.append(f"Context: {deal_context}\n")

    lines.append("## Overall Risk\n")
    lines.append(f"- Overall risk rating: **{result.overallRisk}**\n")

    lines.append("## Key Commercial Terms\n")
    lines.append(f"- **Contract type:** {kc.contractType}")
    lines.append(f"- **Value / pricing basis:** {kc.value}")
    lines.append(f"- **Pricing model:** {kc.pricingModel}")
    lines.append(f"- **Duration / term:** {kc.duration}")
    lines.append(f"- **Renewal / extension:** {kc.renewalTerms}\n")

    lines.append("## Executive Summary\n")
    for bullet in result.executiveSummary:
        lines.append(f"- {bullet}")
    lines.append("")

    lines.append("## Strategic Risk Map\n")
    lines.append("| Category | Risk level | Description | Mitigation |")
    lines.append("| --- | --- | --- | --- |")
    for item in result.riskMatrix:
        lines.append(
            f"| {item.category} | {item.riskLevel} | {item.description} | {item.mitigation} |"
        )
    lines.append("")

    lines.append("## Commercial & Financial Profile\n")
    lines.append(f"- Payment terms & structure: {result.scope.paymentTerms}")
    lines.append(f"- Pricing and billing logic: {result.scope.pricingModel}")
    lines.append(f"- Deliverables / outputs: {result.scope.deliverables}\n")

    lines.append("## Scope of Work & Technical Overview\n")
    lines.append(result.automated_risk_review + "\n")

    lines.append("## Vendor Intelligence\n")
    lines.append(result.vendor_intelligence + "\n")

    lines.append("## Negotiation Coach\n")
    lines.append(result.negotiation_coach + "\n")

    lines.append("## Executive Insights\n")
    lines.append(result.executive_insights + "\n")

    lines.append("## Detailed Deep-Dive Analysis\n")
    lines.append(result.detailedAnalysis + "\n")

    return "\n".join(lines)


# ===========================
# Main dashboard output
# ===========================

result: Optional[AnalysisResult] = st.session_state.analysis_result

if result:
    # ---- Top cards: overall risk & key terms ----
    st.markdown("### Deal Snapshot")

    col1, col2, col3, col4 = st.columns([1.5, 1.2, 1.2, 1.2])

    with col1:
        st.markdown('<div class="ce-card">', unsafe_allow_html=True)
        st.markdown('<div class="label-muted">OVERALL RISK RATING</div>', unsafe_allow_html=True)
        st.markdown(
            f"<h2 style='margin:0.2rem 0 0.3rem 0;'>{result.overallRisk}</h2>",
            unsafe_allow_html=True,
        )
        st.write(result.executiveSummary[0] if result.executiveSummary else "")
        st.markdown("</div>", unsafe_allow_html=True)

    kc = result.keyCommercials

    with col2:
        st.markdown('<div class="ce-card">', unsafe_allow_html=True)
        st.markdown('<div class="label-muted">VALUE / PRICING</div>', unsafe_allow_html=True)
        st.write(kc.value or "Not specified")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="ce-card">', unsafe_allow_html=True)
        st.markdown('<div class="label-muted">TERM</div>', unsafe_allow_html=True)
        st.write(kc.duration or "Not specified")
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="ce-card">', unsafe_allow_html=True)
        st.markdown('<div class="label-muted">CONTRACT TYPE</div>', unsafe_allow_html=True)
        st.write(kc.contractType or "Not specified")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---- Executive summary & deep dive ----
    st.markdown('<div class="section-title">Executive Summary</div>', unsafe_allow_html=True)
    for bullet in result.executiveSummary:
        st.markdown(f"- {bullet}")

    st.markdown('<div class="section-title">Commercial & Financial Profile</div>', unsafe_allow_html=True)
    st.markdown(f"**Contract value / basis:** {kc.value}")
    st.markdown(f"**Pricing model:** {kc.pricingModel}")
    st.markdown(f"**Payment terms:** {result.scope.paymentTerms}")
    st.markdown(f"**Duration:** {kc.duration}")
    st.markdown(f"**Renewal / options:** {kc.renewalTerms}")

    st.markdown('<div class="section-title">Scope of Work & Technical Review</div>', unsafe_allow_html=True)
    st.markdown(f"**Deliverables / services:** {result.scope.deliverables}")
    st.markdown(result.automated_risk_review)

    # ---- Strategic Risk Map ----
    st.markdown('<div class="section-title">Strategic Risk Map</div>', unsafe_allow_html=True)

    # Show risk items as cards
    cols = st.columns(2)
    for idx, item in enumerate(result.riskMatrix):
        col = cols[idx % 2]
        with col:
            st.markdown('<div class="ce-card">', unsafe_allow_html=True)
            st.markdown(
                f"<div class='label-muted'>{item.category}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(risk_badge(item.riskLevel), unsafe_allow_html=True)
            st.write(item.description)
            st.markdown(f"**Mitigation:** {item.mitigation}")
            st.markdown("</div>", unsafe_allow_html=True)

    # ---- Vendor intelligence & negotiation ----
    st.markdown('<div class="section-title">Vendor & Counterparty Intelligence</div>', unsafe_allow_html=True)
    st.markdown(result.vendor_intelligence)

    st.markdown('<div class="section-title">Negotiation Coach</div>', unsafe_allow_html=True)
    st.markdown(result.negotiation_coach)

    st.markdown('<div class="section-title">Executive Insights</div>', unsafe_allow_html=True)
    st.markdown(result.executive_insights)

    # ---- Download report ----
    st.markdown('<div class="section-title">Export Report</div>', unsafe_allow_html=True)
    md_report = build_markdown_report(result, role=role, deal_context=deal_context)
    buffer = io.BytesIO(md_report.encode("utf-8"))
    st.download_button(
        label="Download Report (.md)",
        data=buffer,
        file_name="contract_engine_report.md",
        mime="text/markdown",
    )

    # ---- Raw JSON (optional) ----
    if show_raw_json:
        st.markdown("### Raw JSON Output")
        st.code(result.model_dump_json(indent=2), language="json")
