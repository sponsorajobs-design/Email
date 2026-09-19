export interface DashboardStats {
  total_subscribers: number;
  active_subscribers: number;
  unsubscribed_users: number;
  total_jobs: number;
  live_jobs: number;
  verified_jobs: number;
  dead_jobs: number;
  potential_matches: number;
  queued_emails: number;
  sent_emails: number;
  failed_emails: number;
  dry_run_mode: boolean;
  email_test_mode: boolean;
  test_email_address: string;

  // Campaign Generation & Email Control Center metrics
  todays_campaigns?: number;
  emails_generated?: number;
  subscribers_skipped?: number;
  jobs_selected?: number;
  smtp_failures?: number;
  retries?: number;
  reconciliation_required_records?: number;
}

export interface SystemHealth {
  status: string;
  database: string;
  supabase_configured: boolean;
  supabase_status: string;
  smtp_configured: boolean;
  smtp_host: string;
  smtp_port: number;
  dry_run: boolean;
  email_test_mode: boolean;
  version: string;
}

export interface Job {
  id: number;
  source_job_id: string;
  title: string;
  company: string;
  location?: string;
  description?: string;
  requirements?: string;
  skills?: string;
  experience?: string;
  employment_type?: string;
  application_url: string;
  source_status?: string;
  verification_status: string;
  verification_http_status?: number;
  verification_message?: string;
  final_url?: string;
  verified_at?: string;
}

export interface Subscriber {
  id: number;
  source_subscriber_id: string;
  name: string;
  email: string;
  preferred_roles?: string;
  location?: string;
  skills?: string;
  experience_years?: number;
  subscription_status?: string;
  is_unsubscribed: boolean;
  created_at: string;
  total_emails_sent: number;
  last_email_sent_at?: string;
  last_recommended_job?: string;
  category: string;
  best_match_job_id?: number;
  best_match_job_title?: string;
  best_match_company?: string;
  best_match_score?: number;
  best_match_application_url?: string;
  best_match_url_status?: string;
  email_subject_preview?: string;
  dispatch_readiness: 'READY_TO_SEND' | 'ALREADY_SENT' | 'UNSUBSCRIBED' | 'NO_MATCH' | string;
}

export interface CategorySummary {
  category_name: string;
  total_candidates: number;
  ready_to_send_count: number;
  already_sent_count: number;
  unsubscribed_count: number;
  live_jobs_count: number;
}

export interface SubscriberSentEmailHistoryItem {
  id: number;
  job_id: number;
  job_title: string;
  company_name: string;
  campaign_id?: number;
  campaign_name?: string;
  match_score: number;
  subject: string;
  sent_at?: string;
  message_id?: string;
  status: string;
}

export interface Match {
  id: number;
  subscriber_id: number;
  job_id: number;
  candidate_name?: string;
  candidate_email?: string;
  job_title?: string;
  company_name?: string;
  match_score: number;
  role_score: number;
  skills_score: number;
  experience_score: number;
  location_score: number;
  recency_score: number;
  match_reasons?: string;
  matched_skills?: string;
  unmatched_requirements?: string;
  created_at: string;
}

export interface Campaign {
  id: number;
  name: string;
  status: string;
  total_candidates: number;
  total_matches: number;
  total_queued: number;
  total_sent: number;
  total_failed: number;
  total_skipped: number;
  emails_generated?: number;
  no_eligible_job_count?: number;
  frequency_blocked_count?: number;
  deduplicated_count?: number;
  batch_size: number;
  match_threshold: number;
  notes?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CampaignPreviewItem {
  queue_id: number;
  subscriber_id: number;
  job_id: number;
  candidate_name: string;
  candidate_email: string;
  job_title: string;
  company_name: string;
  match_score: number;
  url_status: string;
  status: string;
  subject: string;
  html_preview: string;
}

export interface CampaignSubscriberItem {
  queue_id: number;
  composition_id?: number;
  subscriber_id: number;
  subscriber_name: string;
  subscriber_email: string;
  preferred_roles?: string;
  country_code?: string;
  frequency?: string;
  job_id: number;
  source_job_id?: string;
  job_title: string;
  company_name: string;
  location?: string;
  job_url: string;
  email_subject: string;
  queue_status: string;
  smtp_status?: string;
  message_id?: string;
  sent_at?: string;
  error_message?: string;
  match_type: string;
}

export interface DecisionTrace {
  subscriber: {
    id: number;
    email: string;
    role: string;
    country: string;
    frequency: string;
  };
  selected_job: {
    id: number;
    source_job_id?: string;
    title: string;
    company: string;
    location?: string;
    country_code?: string;
    published_at?: string;
    quality_score?: number;
  };
  match_type: 'DIRECT' | 'VARIANT' | 'SYNONYM' | 'ALL ROLES' | string;
  ranking_position: number;
  total_eligible_jobs_found?: number;
  match_reason?: string;
  excluded_alternatives?: Array<{
    job_id: number;
    source_job_id?: string;
    title: string;
    company: string;
    match_type: string;
    reason: string;
  }>;
}

export interface CampaignCompositionDetail {
  id: number;
  campaign_id: number;
  queue_id?: number;
  subscriber_id: number;
  job_id: number;
  recipient: string;
  candidate_name?: string;
  subject: string;
  rendered_html: string;
  rendered_text: string;
  template_version: string;
  role_used?: string;
  country_filter?: string;
  frequency?: string;
  job_url: string;
  decision_trace?: DecisionTrace;
  created_at: string;
}

export interface EmailQueueItem {
  id: number;
  campaign_id: number;
  subscriber_id: number;
  job_id: number;
  recipient: string;
  candidate_name?: string;
  job_title?: string;
  company_name?: string;
  match_score: number;
  subject: string;
  status: string;
  skip_reason?: string;
  attempts: number;
  sent_at?: string;
  message_id?: string;
  error_message?: string;
}

export interface AuditLog {
  id: number;
  actor: string;
  action: string;
  details?: string;
  result: string;
  created_at: string;
}

export interface AudienceRecipient {
  id: number;
  name: string;
  email: string;
  preferred_roles?: string;
  location?: string;
}

export interface AudienceCategory {
  category_name: string;
  display_title: string;
  icon: string;
  total_candidates: number;
  recipients: AudienceRecipient[];
}

export interface CustomPreviewRequest {
  job_title: string;
  job_link: string;
  company_name?: string;
  location?: string;
  employment_type?: string;
  custom_subject?: string;
  custom_message?: string;
}

export interface CustomPreviewResponse {
  subject: string;
  html_body: string;
  text_body: string;
  job_url: string;
}

export interface DirectComposeSendRequest {
  job_title: string;
  job_link: string;
  company_name?: string;
  location?: string;
  employment_type?: string;
  selected_categories?: string[];
  selected_subscriber_ids?: number[];
  custom_subject?: string;
  custom_message?: string;
  is_test_send?: boolean;
  test_recipient?: string;
}

