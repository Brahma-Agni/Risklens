import type {
  AnalystAction,
  RiskCase,
  RiskCaseDetail,
  Transaction,
  TransactionInput,
} from '@/lib/types';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8080';
export const ANALYST_ID =
  process.env.NEXT_PUBLIC_ANALYST_ID ?? 'customer-support';
export const HIGH_RISK_THRESHOLD = Number(
  process.env.NEXT_PUBLIC_HIGH_RISK_THRESHOLD ?? '0.75',
);
export const REFRESH_INTERVAL_MS = Number(
  process.env.NEXT_PUBLIC_REFRESH_INTERVAL_MS ?? '10000',
);
export const API_TIMEOUT_MS = Number(
  process.env.NEXT_PUBLIC_API_TIMEOUT_MS ?? '5000',
);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    signal: init?.signal ?? AbortSignal.timeout(API_TIMEOUT_MS),
  });
  if (!response.ok) throw new Error(`RiskLens API returned ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  transactions: (limit = 100) =>
    request<Transaction[]>(`/api/v1/transactions?limit=${limit}`),
  transaction: (transactionId: string) =>
    request<Transaction>(
      `/api/v1/transactions/${encodeURIComponent(transactionId)}`,
    ),
  cases: (limit = 100) =>
    request<RiskCase[]>(`/api/v1/risk-cases?limit=${limit}`),
  highRiskLinkedCases: (limit = 100) =>
    request<RiskCase[]>(`/api/v1/risk-cases/high-risk-linked?limit=${limit}`),
  case: (caseId: string) =>
    request<RiskCaseDetail>(
      `/api/v1/risk-cases/${encodeURIComponent(caseId)}`,
    ),
  analystActions: (limit = 100) =>
    request<AnalystAction[]>(`/api/v1/analyst-actions?limit=${limit}`),
  submitDecision: (caseId: string, decision: string, comment: string) =>
    request(`/api/v1/risk-cases/${encodeURIComponent(caseId)}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, analyst: ANALYST_ID, comment }),
    }),
  simulate: (input: TransactionInput) =>
    request<{
      transactionId: string;
      status: string;
      recommendedAction: string;
      riskScore: number;
      caseId?: string;
      riskServiceAvailable: boolean;
    }>('/api/v1/transactions', { method: 'POST', body: JSON.stringify(input) }),
};

export function money(value: number, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

export function riskPercent(value: number) {
  const normalized = value <= 1 ? value * 100 : value;
  return Math.round(normalized);
}
