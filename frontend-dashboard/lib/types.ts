export type TransactionStatus = string;

export interface Transaction {
  transactionId: string;
  senderId: string;
  receiverId: string;
  amount: number;
  currency: string;
  deviceId?: string;
  ipAddress?: string;
  paymentMethod: string;
  timestamp: string;
  receivedAt?: string;
  status: TransactionStatus;
  riskScore: number;
  caseId?: string;
}

export interface RiskCase {
  caseId: string;
  transactionId: string;
  accountId: string;
  status: string;
  severity: string;
  ringRisk: number;
  confidence: number;
  recommendation: string;
  createdAt: string;
}

export interface RiskSignal {
  type: string;
  source: string;
  score: number;
  description: string;
  evidence?: string;
  createdAt?: string;
}

export interface AnalystDecision {
  id: string;
  decision: string;
  analyst: string;
  comment?: string;
  createdAt: string;
}

export interface AnalystAction extends AnalystDecision {
  caseId: string;
  transactionId: string;
  accountId: string;
}

export interface RiskCaseDetail extends RiskCase {
  transactionRisk: number;
  accountRisk: number;
  behaviorRisk: number;
  temporalRisk: number;
  structuralRisk: number;
  similarityRisk: number;
  aiSummary: string;
  updatedAt: string;
  resolvedAt?: string;
  signals: RiskSignal[];
  decisions: AnalystDecision[];
}

export interface TransactionInput {
  transactionId: string;
  senderId: string;
  receiverId: string;
  amount: number;
  currency: string;
  deviceId: string;
  ipAddress: string;
  paymentMethod: string;
  timestamp: string;
}
