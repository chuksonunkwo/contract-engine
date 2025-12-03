from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from engine import analyze_contract, AnalysisResult


app = FastAPI(
    title="Contract Engine API",
    version="0.2.0",
    description=(
        "Contract analysis engine using OpenAI only.\n\n"
        "Outputs: overallRisk, keyCommercials, executiveSummary, "
        "riskMatrix, scope, compliance, detailedAnalysis."
    ),
)


class AnalyzeRequest(BaseModel):
    contract_text: str
    party_role: Optional[str] = None
    deal_context: Optional[str] = None


class AnalyzeResponse(BaseModel):
    overallRisk: str
    keyCommercials: dict
    executiveSummary: list
    riskMatrix: list
    scope: dict
    compliance: dict
    detailedAnalysis: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    """
    Run the contract engine and return the structured analysis.
    """
    result: AnalysisResult = analyze_contract(
        contract_text=request.contract_text,
        party_role=request.party_role,
        deal_context=request.deal_context,
    )

    return AnalyzeResponse(
        overallRisk=result.overallRisk,
        keyCommercials=result.keyCommercials.dict(),
        executiveSummary=result.executiveSummary,
        riskMatrix=[item.dict() for item in result.riskMatrix],
        scope=result.scope.dict(),
        compliance=result.compliance.dict(),
        detailedAnalysis=result.detailedAnalysis,
    )
