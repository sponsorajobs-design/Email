import React from 'react'
import { DashboardStats } from '../types'

interface StatsCardsProps {
  stats: DashboardStats | null
}

export const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
  if (!stats) return null

  const coreItems = [
    {
      label: 'Active Subscribers',
      value: stats.active_subscribers,
      subtext: `${stats.total_subscribers} total (${stats.unsubscribed_users} unsubscribed)`,
      color: '#38bdf8'
    },
    {
      label: 'Verified Live Jobs',
      value: stats.verified_jobs,
      subtext: `${stats.live_jobs} active (${stats.dead_jobs} dead/flagged)`,
      color: '#10b981'
    },
    {
      label: 'Today\'s Campaigns',
      value: stats.todays_campaigns ?? 0,
      subtext: 'Created today (UTC)',
      color: '#818cf8'
    },
    {
      label: 'Emails Generated',
      value: stats.emails_generated ?? 0,
      subtext: `${stats.jobs_selected ?? 0} distinct jobs selected`,
      color: '#38bdf8'
    },
    {
      label: 'Emails Queued',
      value: stats.queued_emails,
      subtext: 'Staged for delivery',
      color: '#f59e0b'
    },
    {
      label: 'Emails Sent',
      value: stats.sent_emails,
      subtext: 'Delivered via SMTP',
      color: '#34d399'
    },
    {
      label: 'Emails Failed',
      value: stats.failed_emails,
      subtext: `${stats.smtp_failures ?? 0} SMTP failures`,
      color: stats.failed_emails > 0 ? '#f43f5e' : '#94a3b8'
    },
    {
      label: 'Subscribers Skipped',
      value: stats.subscribers_skipped ?? 0,
      subtext: 'Frequency/no-job gating',
      color: '#94a3b8'
    },
    {
      label: 'Retries & Reconcile',
      value: (stats.retries ?? 0) + (stats.reconciliation_required_records ?? 0),
      subtext: `${stats.retries ?? 0} retries, ${stats.reconciliation_required_records ?? 0} reconcile`,
      color: (stats.reconciliation_required_records ?? 0) > 0 ? '#fb923c' : '#64748b'
    }
  ]

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div className="stats-grid">
        {coreItems.map((item, idx) => (
          <div key={idx} className="stat-card">
            <div className="stat-label">{item.label}</div>
            <div className="stat-value" style={{ color: item.color }}>
              {item.value.toLocaleString()}
            </div>
            <div className="stat-subtext">{item.subtext}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
