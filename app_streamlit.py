import os
from typing import Optional

import streamlit as st

from engine import analyze_contract, AnalysisResult


# ---------------------------------------------------------
# Simple check for API key (for local dev and Render)
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
# Streamlit layout helpers
# ---------------------------------------------------------
def render_header():
    st.set_page_config(
        page_title="Contract Engine",
        page_icon="📑",
        layout="wide",
    )

    st.title("📑 Contract Engine")
    st.caption(
        "Senior contract analysis assistant for Contracts & Procurement "
        "in oil & gas – powered by OpenAI."
    )


def render_sidebar() -> dict:
    st.sidebar.header("Input Settings")

    party_role = st.sidebar.selectbox(
        "Your role in this contract",
        options=[
            "buyer",
            "customer",
            "client",
            "seller",
            "vendor",
            "service_provider",
        ],
        index=0,
    )

    deal_context = st.sidebar.text_area(
        "Deal context (optional)",
        value="",
        height=120,
        help="Describe criticality, geography, value, strategic importance, etc.",
    )

    run_button = st.sidebar.button("Run Analysis 🚀")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Notes")
    st.sidebar.write(
        "- Paste contract text in the main panel.\n"
        "- Output is structured for dashboards and reports.\n"
        "- Keep sensitive data secure in production deployments."
    )

    return {
        "party_role": party_role,
        "deal_context": deal_context,
        "run_button": run_button,
    }


def render_input_area() -> str:
    st.subheader("Contract Text")
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
        height=300,
        placeholder="Paste or type the full contract here...",
    )

    return contract_text


def render_executive_summary(result: AnalysisResult):
    st.subheader("Executive Summary (BLUF)")

    if not result.executiveSummary:
        st.info("No executive summary generated.")
        return

    for bullet in result.executiveSummary:
        # Ensure each bullet is rendered as a list item
        if not bullet.strip().startswith("-"):
            st.markdown(f"- {bullet}")
        else:
            st.markdown(bullet)


def render_key_commercials(result: AnalysisResult):
    st.subheader("Key Commercials")

    kc = result.keyCommercials
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Overall Risk", result.overallRisk)

    with col2:
        st.write("**Contract Value**")
        st.write(kc.value or "Not specified")

    with col3:
        st.write("**Duration**")
        st.write(kc.duration or "Not specified")

    col4, col5 = st.columns(2)
    with col4:
        st.write("**Contract Type**")
        st.write(kc.contractType or "Not specified")
    with col5:
        st.write("**Pricing Model**")
        st.write(kc.pricingModel or "Not specified")

    if kc.renewalTerms:
        st.write("**Renewal Terms**")
        st.write(kc.renewalTerms)


def render_risk_matrix(result: AnalysisResult):
    st.subheader("Risk Matrix")

    if not result.riskMatrix:
        st.info("No risk matrix items generated.")
        return

    for item in result.riskMatrix:
        with st.expander(f"{item.category} – {item.riskLevel}"):
            st.write(f"**Description**: {item.description}")
            if item.mitigation:
                st.write(f"**Mitigation**: {item.mitigation}")


def render_scope(result: AnalysisResult):
    st.subheader("Scope, Pricing & Deliverables")

    scope = result.scope

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Pricing Model**")
        st.write(scope.pricingModel or "Not specified")
    with col2:
        st.write("**Payment Terms**")
        st.write(scope.paymentTerms or "Not specified")

    st.write("**Key Deliverables / Services**")
    if scope.deliverables:
        for d in scope.deliverables:
            st.markdown(f"- {d}")
    else:
        st.write("Not specified")


def render_compliance(result: AnalysisResult):
    st.subheader("Compliance & Counterparty View")

    comp = result.compliance

    st.write("**Summary**")
    st.write(comp.summary)

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Overall Compliance Risk**")
        st.write(comp.overallComplianceRisk)
    with col2:
        st.write("**Financial Signals**")
        if comp.financialSignals:
            for s in comp.financialSignals:
                st.markdown(f"- {s}")
        else:
            st.write("None identified")

    st.write("**Sanctions Flags**")
    if comp.sanctionsFlags:
        for s in comp.sanctionsFlags:
            st.markdown(f"- {s}")
    else:
        st.write("None identified")

    st.write("**Adverse Media**")
    if comp.adverseMedia:
        for s in comp.adverseMedia:
            st.markdown(f"- {s}")
    else:
        st.write("None identified")


def render_detailed_analysis(result: AnalysisResult):
    st.subheader("Detailed Analysis (McKinsey-style Markdown)")
    st.markdown(result.detailedAnalysis)


def render_raw_json(result: AnalysisResult):
    st.subheader("Raw JSON Output")
    st.json(result.dict())


# ---------------------------------------------------------
# Main app
# ---------------------------------------------------------
def main():
    render_header()
    api_key = ensure_api_key()
    settings = render_sidebar()
    contract_text = render_input_area()

    if settings["run_button"]:
        if not api_key:
            st.stop()

        if not contract_text.strip():
            st.error("Please paste contract text before running analysis.")
            st.stop()

        with st.spinner("Analyzing contract with Contract Engine..."):
            try:
                result: AnalysisResult = analyze_contract(
                    contract_text=contract_text,
                    party_role=settings["party_role"],
                    deal_context=settings["deal_context"],
                )
            except Exception as e:
                st.error(f"Error during analysis: {e}")
                st.stop()

        # Layout tabs for different views
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            [
                "Executive Summary",
                "Key Commercials",
                "Risk Matrix",
                "Scope",
                "Compliance",
                "Detailed Analysis",
            ]
        )

        with tab1:
            render_executive_summary(result)
        with tab2:
            render_key_commercials(result)
        with tab3:
            render_risk_matrix(result)
        with tab4:
            render_scope(result)
        with tab5:
            render_compliance(result)
        with tab6:
            render_detailed_analysis(result)

        # Optional: show raw JSON below tabs
        st.markdown("---")
        render_raw_json(result)


if __name__ == "__main__":
    main()
