# engine.py

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

import os

# -----------------------
# OpenAI Client
# -----------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# -----------------------
# Pydantic Models
# -----------------------

class RiskItem(BaseModel):
    category: str
    riskLevel: str
    description: str
    mitigation: str


class KeyCommercials(BaseModel):
    value: str
    duration: str
    contractType: str
    pricingModel: str
    renewalTerms: str


class ScopeModel(BaseModel):
    deliverables: str
    paymentTerms: str
    pricingModel: str


class AnalysisResult(BaseModel):
    overallRisk: str
    keyCommercials: KeyCommercials
    executiveSummary: List[str]
    riskMatrix: List[RiskItem]
    scope: ScopeModel

    automated_risk_review: str
    vendor_intelligence: str
    negotiation_coach: str
    executive_insights: str
    detailedAnalysis: str


# -----------------------
# SYSTEM PROMPT (AI ENGINE)
# -----------------------

SYSTEM_PROMPT = """
You are Contract Engine – an Oil & Gas contract analysis system.

You extract:
- Key Commercials
- Scope of Work
- Risk Matrix (Liability, HSE, Payment, Termination, Legal)
- Executive Insights
- Vendor Intelligence (no personal data, only public-facing insights)
- Negotiation guidance
- A structured deep-dive

Rules:
- NEVER mention “McKinsey” or any consulting brand.
- NEVER say you are a law firm.
- Keep output concise, in bullet points, professional.
- Produce a complete risk matrix (5 categories minimum).
- Always return structured data that matches the schema strictly.
"""

# -----------------------
# CONTRACT ANALYSIS FUNCTION
# -----------------------

def analyze_contract(text: str, role: str = "buyer", deal_context: str = "") -> AnalysisResult:

    USER_PROMPT = f"""
Analyze the following Oil & Gas contract:

ROLE: {role}
ADDITIONAL CONTEXT: {deal_context}

Return a JSON dictionary EXACTLY with the fields:

{{
  "overallRisk": "",
  "keyCommercials": {{
      "value": "",
      "duration": "",
      "contractType": "",
      "pricingModel": "",
      "renewalTerms": ""
  }},
  "executiveSummary": [],
  "riskMatrix": [
      {{
         "category": "Liability",
         "riskLevel": "",
         "description": "",
         "mitigation": ""
      }},
      {{
         "category": "HSE",
         "riskLevel": "",
         "description": "",
         "mitigation": ""
      }},
      {{
         "category": "Payment",
         "riskLevel": "",
         "description": "",
         "mitigation": ""
      }},
      {{
         "category": "Termination",
         "riskLevel": "",
         "description": "",
         "mitigation": ""
      }},
      {{
         "category": "Legal",
         "riskLevel": "",
         "description": "",
         "mitigation": ""
      }}
  ],
  "scope": {{
      "deliverables": "",
      "paymentTerms": "",
      "pricingModel": ""
  }},
  "automated_risk_review": "",
  "vendor_intelligence": "",
  "negotiation_coach": "",
  "executive_insights": "",
  "detailedAnalysis": ""
}}

CONTRACT TEXT:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ]
    )

    data = response.choices[0].message.content
    return AnalysisResult.model_validate_json(data)


# -----------------------
# LICENSE VALIDATION
# -----------------------

def validate_license(key: str):
    """
    Dummy local validation for development.
    Replace with real Gumroad API call on deployment.
    """
    if not key or len(key) < 8:
        return False, "Invalid license key format."

    # DEV MODE — always pass
    return True, "License verified successfully."
