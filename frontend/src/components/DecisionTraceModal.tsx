import React from 'react'
import { DecisionTrace, CampaignSubscriberItem } from '../types'

interface DecisionTraceModalProps {
  item: CampaignSubscriberItem | null
  trace: DecisionTrace | null
  loading: boolean
  onClose: () => void
}

export const DecisionTraceModal: React.FC<DecisionTraceModalProps> = ({
  item,
  trace,
  loading,
  onClose
}) => {
  if (!item) return null

  const getMatchTypeBadge = (type?: string) => {
    switch (type) {
      case 'DIRECT':
        return <span className="badge badge-live" style={{ background: '#059669', color: '#ffffff' }}>DIRECT (Level 3)</span>
      case 'VARIANT':
        return <span className="badge badge-redirect" style={{ background: '#2563eb', color: '#ffffff' }}>VARIANT (Level 2)</span>
      case 'SYNONYM':
        return <span className="badge badge-redirect" style={{ background: '#d97706', color: '#ffffff' }}>SYNONYM (Level 1)</span>
      case 'ALL ROLES':
        return <span className="badge badge-unknown" style={{ background: '#64748b', color: '#ffffff' }}>ALL ROLES (Level 0)</span>
      default:
        return <span className="badge badge-unknown">{type || 'EVALUATED'}</span>
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '680px' }}>
        <div className="modal-header">
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)' }}>
              🎯 Decision Trace: Why This Job?
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Deterministic role evaluation, ranking hierarchy, and exclusion audit trace.
            </p>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
            Loading decision trace...
          </div>
        ) : (
          <div>
            {/* Subscriber Preferences Card */}
            <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#334155', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Subscriber Profile & Gating
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '13px' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Subscriber: </span>
                  <strong>{trace?.subscriber.email || item.subscriber_email}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Preferred Role: </span>
                  <strong style={{ color: '#2563eb' }}>{trace?.subscriber.role || item.preferred_roles || 'All Roles'}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Country Filter: </span>
                  <strong>{trace?.subscriber.country || item.country_code || 'ALL'}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Frequency: </span>
                  <span style={{ textTransform: 'uppercase', fontWeight: 700, color: '#059669' }}>
                    {trace?.subscriber.frequency || item.frequency || 'DAILY'}
                  </span>
                </div>
              </div>
            </div>

            {/* Selected Job Card */}
            <div style={{ background: 'rgba(37, 99, 235, 0.04)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', border: '1px solid rgba(37, 99, 235, 0.2)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ fontSize: '13px', fontWeight: '700', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Selected Winner (Max 1 Job)
                </div>
                <div>
                  {getMatchTypeBadge(trace?.match_type || item.match_type)}
                </div>
              </div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: '#0f172a', marginBottom: '4px' }}>
                {trace?.selected_job.title || item.job_title}
              </div>
              <div style={{ fontSize: '13px', color: '#475569', marginBottom: '8px' }}>
                {trace?.selected_job.company || item.company_name} • {trace?.selected_job.location || item.location || 'United Kingdom'}
              </div>
              <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#64748b' }}>
                <div>Ranking Position: <strong style={{ color: '#059669' }}>#{trace?.ranking_position || 1}</strong></div>
                <div>Total Candidates Evaluated: <strong>{trace?.total_eligible_jobs_found || 1}</strong></div>
                {trace?.match_reason && <div>Match Reason: <em>{trace.match_reason}</em></div>}
              </div>
            </div>

            {/* Excluded Alternatives */}
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#475569', marginBottom: '8px' }}>
                Excluded Alternatives & Ranking Order
              </div>
              {trace?.excluded_alternatives && trace.excluded_alternatives.length > 0 ? (
                <div style={{ maxHeight: '180px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                  <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                    <thead style={{ background: '#f8fafc', position: 'sticky', top: 0 }}>
                      <tr>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Job Title & Company</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Match Type</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Exclusion / Ranking Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trace.excluded_alternatives.map((alt, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '6px 10px' }}>
                            <strong>{alt.title}</strong>
                            <div style={{ color: '#64748b', fontSize: '11px' }}>{alt.company}</div>
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={{ fontSize: '11px' }}>{alt.match_type}</span>
                          </td>
                          <td style={{ padding: '6px 10px', color: '#64748b' }}>
                            {alt.reason}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic', padding: '8px', background: '#f8fafc', borderRadius: 'var(--radius-sm)' }}>
                  No competing alternative matching jobs were available in this inventory cycle.
                </div>
              )}
            </div>

            {/* Close Button */}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-primary" onClick={onClose}>
                Close Trace
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
