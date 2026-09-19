export interface Membership { id: string; group_id: string; group: string; role: string; label: string; }
export interface Session { user: { username: string; display_name: string }; active: Membership; memberships: Membership[]; }
export interface PracticeSummary {
  id: string; client_id: string; client_name?: string; practice_type_code: string;
  period_start: string; period_end: string; due_date: string; status: string;
  progress: { completed: number; total: number; percent: number };
  situation: { code: string; label: string }; urgency: { level: string; label: string; detail: string };
  waiting_hours?: number; waiting_since?: string; validated_at?: string; validation_outcome?: string; validation_note?: string;
}
export interface Evidence {
  id: string; filename: string; content_type: string; description: string; document_type: string;
  actor: string; created_at: string; preview_url: string; download_url: string; related_task_code: string | null;
}
export interface Result {
  id: string; action: string; outcome: string; note: string; actor: string; actor_role: string;
  timestamp: string; related_task_code: string | null; related_task_title?: string; evidence_ids: string[]; evidence?: Evidence[];
}
export interface Task {
  code: string; title: string; instructions: string; status: string; active: boolean; required: boolean;
  assigned_group: string; claimed_by: string | null; completed_by: string | null; due_date: string;
  depends_on: string[]; outcomes: string[]; transitions: Record<string, string[]>;
  result_id: string | null; work_note: string; reopen_reason: string;
}
export interface QueueTask extends Task {
  practice_id: string; practice_type_code: string; client_id: string; client_name?: string; queue_section: string;
  completed_at?: string; outcome?: string; result_note?: string;
}
export interface AuditEvent { event_type: string; actor: string; at: string; details: Record<string, unknown>; }
export interface Practice {
  id: string; client_id: string; practice_type_code: string; period_start: string; period_end: string;
  due_date: string; status: string; tasks: Task[]; nonconformities: NonConformity[]; requires_validation: boolean;
  progress: { completed: number; total: number }; results: Result[]; evidence: Evidence[]; audit: AuditEvent[];
}
export interface TaskDetail {
  practice: { id: string; type: string; client_id: string; period_start: string; period_end: string; due_date: string };
  task: Task; task_results?: Result[]; previous_results?: Result[]; evidence?: Evidence[]; task_progress_evidence: Evidence[];
  task_journal: { type: string; actor: string; at: string; note: string; evidence: Evidence[] }[];
}
export interface Attachment { filename: string; content_type: string; description: string; document_type: string; content_base64: string; }
export interface NonConformity {
  id: string; reason: string; status: string; opened_by: string; opened_at: string; closed_by: string | null; closed_at: string | null;
  corrective_actions: { id: string; actor: string; instruction: string; task_codes: string[]; created_at: string; completed_at: string | null }[];
}
