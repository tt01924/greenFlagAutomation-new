/**
 * Type definitions for Green Flag Automation frontend
 */

export interface Ticket {
  id: string
  ticket_id: string
  ticket_key: string
  action: 'auto_respond' | 'escalate' | 'shadow'
  matched_response_id: string | null
  escalation_reason: string | null
  created_at: string
  comment_id: string | null
  retracted_at: string | null
  retracted_by: string | null
  processing_duration_ms: number | null
  ticket_summary: string
}

export interface TicketDetail extends Ticket {
  summary: string
  description: string
  reporter: string
  created: string
  confidence_scores: Record<string, { confidence: number; reasoning: string }>
  comment_posted_at: string | null
  system_version: string
  config_version: string
  jira_url: string
}

export interface Escalation {
  id: string
  ticket_key: string
  escalation_reason: string
  created_at: string
  is_overdue: boolean
  ticket_summary: string
  reporter: string
  confidence_scores: Record<string, { confidence: number; reasoning: string }>
}

export interface WeeklyReport {
  week_start: string
  week_end: string
  statistics: {
    total_tickets: number
    auto_responded: number
    escalated: number
    shadow: number
    retracted: number
    automation_rate: number
    false_positive_rate: number
  }
  top_responses: Array<{ response_id: string; count: number }>
  top_escalation_reasons: Array<{ reason: string; count: number }>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
