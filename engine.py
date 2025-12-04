from typing import Optional, List, Literal
from pydantic import BaseModel
import os
import json

from openai import OpenAI


# =========================================================
# 1) OUTPUT MODELS – SCHEMA
# =========================================================

RiskLevel = Literal["High", "Medium", "Low", "Unknown"]
DecisionRecommendation = Literal[
    "approve", "approve_with_conditions", "renegotiate", "do_not_approve"
]


class KeyCommercials(BaseModel):
    value: Optional[str]
    duration: Optional[str]
    contractType: Optional[str]
    pricingModel: Optional[str]
    renewalTerms: Optional[str]


class RiskMatrixItem(BaseModel):
    category: Literal["Liability", "HSE", "Payment", "Termination", "Legal"]
    riskLevel: RiskLevel
    description: str
    mitigation: Optional[str]


class ScopeInfo(BaseModel):
    pricingModel: Optional[str]
    paymentTerms: Optional[str]
    deliverables: List[str]


class ComplianceInfo(BaseModel):
    summary: str
    overallComplianceRisk: Literal["High", "Medium", "Low", "Unknown"]
    sanctionsFlags: List[str]
    adverseMedia: List[str]
    financialSignals: List[str]


class AnalysisResult(BaseModel):
    overallRisk: RiskLevel
    keyCommercials: KeyCommercials
    executiveSummary: List[str]
    riskMatrix: List[RiskMatrixItem]
    scope: ScopeInfo
    compliance: ComplianceInfo
    detailedAnalysis: str


# =========================================================
# 2) SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are Contract Engine, a senior contract management specialist supporting the Contracts & Procurement function of a large oil & gas company.

Your responsibilities:
- Read the entire contract carefully.
- Extract structured data for dashboards.
- Produce a detailed written report using McKinsey-style synthesis.
- Maintain strict JSON formatting as requested by the user prompt.
- Think like a senior commercial, legal, and procurement professional.

STYLE & QUALITY RULES:
- Synthesis over summary (always explain “so what?” and business impact).
- Active voice only (e.g., “Contractor bears full liability.”).
- Strict bullet points: each item on a new line with a hyphen (-).
- Data-driven: extract numbers, amounts, caps, deadlines, durations, formulas.
- BLUF (Bottom Line Up Front): prioritize executive relevance.

STRUCTURED OUTPUT EXPECTATIONS:
You must populate all fields of the required JSON schema:
- overallRisk (High, Medium, Low, or Unknown if genuinely unclear)
- keyCommercials (value, duration, contractType, pricingModel, renewalTerms)
- executiveSummary (3–5 BLUF bullets, each starting with a hyphen)
- riskMatrix (array of risk items with categories: Liability, HSE, Payment, Termination, Legal, with riskLevel High/Medium/Low/Unknown)
- scope (pricing model, payment terms, deliverables)
- compliance (sanctions, adverse media, financial signals, overallComplianceRisk)
- detailedAnalysis (Markdown deep-dive using the required headings)

DETAILED ANALYSIS FORMAT (Markdown):
You MUST structure the deep-dive using the following sections:
## Commercial & Financial Profile
## Scope of Work & Technical Review
## Liquidated Damages and Service Credits
## Liability, Indemnities, Insurance
## HSE, Operational and Performance Risk
## Term, Termination, Breach and Force Majeure
## Legal, Compliance and Governance
## Strategic Recommendations
- Use bullet points under sub-sections where appropriate.
- Each bullet point must appear on its own line.
- Do NOT repeat the executive summary or risk matrix inside this Markdown.

COMPLIANCE FIELD:
- You do NOT have access to live web search tools.
- Base the 'compliance' section on signals from the contract text and general domain knowledge.
- If there is not enough information, clearly state assumptions and set overallComplianceRisk to "Unknown" or a conservative value.
- Do not claim that you used external search tools or sanctions databases.

CRITICAL INSTRUCTIONS:
- You must always return EXACT JSON with no text outside the JSON block.
- Do not add commentary, explanations, apologies, or Markdown outside JSON.
- Ensure all strings are valid JSON string values.
- Maintain professional tone suitable for oil & gas contract leadership.
"""


# =========================================================
# 3) OPENAI CLIENT
# =========================================================

def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. In PowerShell, run:\n"
            "$env:OPENAI_API_KEY = 'YOUR_API_KEY_HERE'"
        )
    return OpenAI(api_key=api_key)


# =========================================================
# 4) CORE FUNCTION
# =========================================================

def analyze_contract(
    contract_text: str,
    party_role: Optional[str] = None,
    deal_context: Optional[str] = None,
) -> AnalysisResult:
    """
    Call OpenAI once and ask it to produce a JSON object with your schema.
    If the JSON is malformed, do a second "repair" call.
    """

    client = get_openai_client()

    role_text = party_role or "unspecified"
    context_text = deal_context or "No additional context provided."

    user_prompt = f"""
You will receive a contract and must produce a structured analysis suitable for a management dashboard and a detailed written report.

The requesting party role is: {role_text}.
Deal context: {context_text}.

Contract text:
\"\"\"{contract_text}\"\"\"

Return ONE JSON object with this exact structure (field names and types):

{{
  "overallRisk": "High | Medium | Low | Unknown",
  "keyCommercials": {{
    "value": "string or null",
    "duration": "string or null",
    "contractType": "string or null",
    "pricingModel": "string or null",
    "renewalTerms": "string or null"
  }},
  "executiveSummary": [
    "string",
    "string",
    "string"
  ],
  "riskMatrix": [
    {{
      "category": "Liability | HSE | Payment | Termination | Legal",
      "riskLevel": "High | Medium | Low | Unknown",
      "description": "string",
      "mitigation": "string or null"
    }}
  ],
  "scope": {{
    "pricingModel": "string or null",
    "paymentTerms": "string or null",
    "deliverables": ["string", "string"]
  }},
  "compliance": {{
    "summary": "string",
    "overallComplianceRisk": "High | Medium | Low | Unknown",
    "sanctionsFlags": ["string", "string"],
    "adverseMedia": ["string", "string"],
    "financialSignals": ["string", "string"]
  }},
  "detailedAnalysis": "Markdown string following the required headings"
}}

Rules:
- Respond with JSON only, no markdown fences, no backticks.
- All string values must be valid JSON strings.
- In executiveSummary, each bullet should conceptually be a BLUF-style bullet; you may include Markdown formatting such as **bold** inside the string.
- In detailedAnalysis, follow the required headings and use bullet points where appropriate, one per line.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        max_tokens=2000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = (response.choices[0].message.content or "").strip()

    # ------------------------------------------------------------------
    # 1st attempt: normal JSON parse
    # ------------------------------------------------------------------
    data = None
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # ------------------------------------------------------------------
        # 2nd attempt: tolerant parser
        # ------------------------------------------------------------------
        try:
            decoder = json.JSONDecoder(strict=False)
            data = decoder.decode(content)
        except json.JSONDecodeError:
            # ------------------------------------------------------------------
            # 3rd attempt: call model again to "repair" the JSON
            # ------------------------------------------------------------------
            repair_prompt = f"""
You are a JSON repair assistant.

You will receive malformed JSON that is supposed to follow the contract analysis schema you already know.
Your task is to output a corrected JSON object that:
- Is valid JSON.
- Matches the expected schema and field names.
- Does not contain any markdown fences or extra commentary.

Malformed JSON:
```json
{content}
```"""

            repair_response = client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0.0,
                max_tokens=2000,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You repair JSON to be valid and schema-compliant."},
                    {"role": "user", "content": repair_prompt},
                ],
            )

            repaired = (repair_response.choices[0].message.content or "").strip()
            data = json.loads(repaired)

    # Map JSON into Pydantic models
    result = AnalysisResult(
        overallRisk=data["overallRisk"],
        keyCommercials=KeyCommercials(**data["keyCommercials"]),
        executiveSummary=list(data.get("executiveSummary", [])),
        riskMatrix=[RiskMatrixItem(**item) for item in data.get("riskMatrix", [])],
        scope=ScopeInfo(**data["scope"]),
        compliance=ComplianceInfo(**data["compliance"]),
        detailedAnalysis=data["detailedAnalysis"],
    )

    return result


# =========================================================
# 5) SIMPLE LOCAL TEST
# =========================================================

if __name__ == "__main__":
    sample_contract = "This is a short sample contract for testing only."
    result = analyze_contract(
        sample_contract,
        party_role="buyer",
        deal_context="Internal test of the engine.",
    )
    print(result.dict())
