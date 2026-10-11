export interface HealthStatus {
  status: string;
  version: string;
  database: string;
  llm_configured: boolean;
}

export interface DatabaseStats {
  size_bytes: number;
  size_mb: number;
  experiments_count: number;
  runs_count: number;
  events_count: number;
  llm_calls_count: number;
}

export interface SystemStatus {
  version: string;
  active_experiment_id: string | null;
  is_busy: boolean;
  database_stats: DatabaseStats;
  limits: {
    max_sim_time_default: number;
    max_events_default: number;
    max_wall_seconds_default: number;
  };
}

export interface RunMetricsSummary {
  messages_sent: number;
  messages_delivered: number;
  messages_dropped: number;
  drops_by_reason?: Record<string, number>;
  messages_duplicated: number;
  messages_reordered: number;
  acks_sent: number;
  acks_received: number;
  acks_unmatched: number;
  timeouts: number;
  retransmissions: number;
  retries_exhausted: number;
  duplicates_suppressed: number;
  stale_updates_rejected: number;
  sync_requests: number;
  sync_responses: number;
  sync_applied: number;
  recoordination_attempts: number;
  degraded_peers: number;
  invalid_rejected: number;
  messages_needing_recovery: number;
  messages_recovered: number;
  recovery_success_rate: number;
  mean_recovery_latency: number;
  simulated_time: number;
  wall_ms: number;
  validation_valid: boolean;
  violations_count: number;
}

export interface RunRecord {
  id: string;
  experiment_id: string;
  mode: string;
  seed: number;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  outcome: 'valid' | 'invalid' | 'incomplete' | 'failed' | 'cancelled' | 'interrupted' | 'pending';
  termination_reason: string;
  started_at: string;
  ended_at: string | null;
  simulated_time: number;
  wall_ms: number;
  validation_valid: boolean;
  violations_count: number;
  metrics_summary: RunMetricsSummary;
  error_message?: string | null;
}

export interface ExperimentRecord {
  id: string;
  name: string;
  created_at: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  config: any;
  seeds: number[];
  agent_type: 'deterministic' | 'llm';
  provider_model?: string | null;
  code_version: string;
  schema_version: string;
  total_runs: number;
  completed_runs: number;
  error_message?: string | null;
  runs?: RunRecord[];
}

export interface SimEvent {
  id?: number;
  run_id: string;
  seq: number;
  sim_time: number;
  type: string;
  agent_id?: string | null;
  target_agent_id?: string | null;
  msg_id?: string | null;
  payload: Record<string, any>;
}

export interface ModeSummaryStats {
  n: number;
  valid_count: number;
  valid_rate: number;
  valid_rate_ci_lower: number;
  valid_rate_ci_upper: number;
  deadlock_count: number;
  deadlock_rate: number;
  mean_simulated_time: number;
  simulated_time_ci_lower: number;
  simulated_time_ci_upper: number;
  median_simulated_time: number;
  iqr_simulated_time: number;
  mean_messages_sent: number;
  recovery_success_rate: number;
}

export interface AnalyticsSummaryResponse {
  modes: Record<string, ModeSummaryStats>;
  paired_tests: Record<string, any>;
  paired_fault_free_only: boolean;
}
