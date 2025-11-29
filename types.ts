
export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  isError?: boolean;
}

export enum AnalysisStatus {
  IDLE = 'IDLE',
  ANALYZING = 'ANALYZING',
  COMPLETE = 'COMPLETE',
  ERROR = 'ERROR'
}

export interface RiskItem {
  category: string;
  level: 'High' | 'Medium' | 'Low';
  description: string;
}

export interface ScopeData {
  pricingModel: string;
  paymentTerms: string;
  keyDeliverables: string[];
  serviceLevels: string;
}

export interface ComplianceData {
  entityName: string;
  sanctionsCheck: { status: 'Clean' | 'Warning' | 'Critical'; details: string };
  financialHealth: { status: 'Stable' | 'Concern' | 'Unknown'; details: string };
  reputationCheck: { status: 'Clean' | 'Adverse Media' | 'Unknown'; details: string };
}

export interface ContractAnalysis {
  overallRisk: {
    level: 'High' | 'Medium' | 'Low';
    score: number; // 0-100
    reasoning: string;
  };
  keyCommercials: {
    value: string;
    duration: string;
    contractType: string;
  };
  riskMatrix: RiskItem[];
  executiveSummary: string;
  detailedAnalysis: string;
  scope: ScopeData;
  compliance: ComplianceData;
}

export interface AnalysisState {
  status: AnalysisStatus;
  result: ContractAnalysis | null;
  error: string | null;
}

export interface ContractFile {
  type: 'text' | 'pdf' | 'docx';
  content: string; // Plain text or Base64 string for PDF
  name?: string;
  mimeType?: string;
}
