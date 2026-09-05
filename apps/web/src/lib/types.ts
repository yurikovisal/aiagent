export interface UserInfo {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department?: string | null;
  permissions: string[];
}

export interface RiskItem {
  id: number;
  fingerprint: string;
  rule_key: string;
  domain: string;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  title: string;
  cause: string;
  impact: string;
  recommendation: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  score: number;
  status: string;
  evidence: { fact: string; source: string; record_id?: unknown; confidence?: number }[];
  related_order_id?: number | null;
  first_detected_at: string;
  last_detected_at: string;
}

export interface ApprovalItem {
  id: number;
  title: string;
  description: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  risk: string;
  status: string;
  proposed_by_agent: string;
  evidence: { fact: string; source: string }[];
  created_at: string;
  decided_at?: string | null;
  decision_comment?: string;
  execution_result?: Record<string, unknown> | null;
}

export interface ChatSource {
  source: string;
  record_id: unknown;
  timestamp: string;
  confidence: number;
}

export interface OrchestrationResult {
  run_id: string;
  status: string;
  summary: string;
  risks: RiskItem[];
  findings: Record<string, unknown>[];
  recommendations: string[];
  actions_proposed: Record<string, unknown>[];
  sources: ChatSource[];
  per_domain: Record<string, unknown>;
  confidence: number;
  confidence_label: string;
  conversation_id?: number;
}

export interface ExecutiveBrief {
  generated_at: string;
  executive_summary: string;
  attention_count: number;
  sections: Record<string, unknown>;
  overdue_orders: Record<string, unknown>[];
}

export interface HealthCheck {
  status: string;
  checks: Record<string, { status: string; [key: string]: unknown }>;
  app_env: string;
}

export interface AgentStats {
  active_runs: number;
  completed_runs: number;
  failed_runs: number;
  total_runs: number;
  avg_duration_ms: number;
  tool_calls_total: number;
  llm_calls_total: number;
  avg_tokens_per_sec: number;
  pending_approvals: number;
}
