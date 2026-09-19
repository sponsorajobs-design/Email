import React, { useState } from 'react'
import { CampaignCompositionDetail, CampaignSubscriberItem, CampaignPreviewItem } from '../types'
import { api } from '../services/api'

interface EmailPreviewModalProps {
  composition?: CampaignCompositionDetail | null
  item?: CampaignSubscriberItem | CampaignPreviewItem | null
  campaignId?: number
  loading?: boolean
  onClose: () => void
  onItemSent?: (queueId: number) => void
}

export const EmailPreviewModal: React.FC<EmailPreviewModalProps> = ({
  composition,
  item,
  campaignId,
  loading = false,
  onClose,
  onItemSent
}) => {
  const [viewMode, setViewMode] = useState<'html' | 'text'>('html')
  const [sending, setSending] = useState(false)
  const [sendSuccess, setSendSuccess] = useState<string | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)

  if (!item && !composition) return null

  // Support both CampaignSubscriberItem and legacy CampaignPreviewItem
  const subItem = item as any
  const recipient = composition?.recipient || subItem?.subscriber_email || subItem?.candidate_email || ''
  const candidateName = composition?.candidate_name || subItem?.subscriber_name || subItem?.candidate_name || 'Subscriber'
  const subject = composition?.subject || subItem?.email_subject || subItem?.subject || ''
  const role = composition?.role_used || subItem?.job_title || ''
  const company = subItem?.company_name || 'Partner'
  const location = subItem?.location || 'United Kingdom'
  const jobUrl = composition?.job_url || subItem?.job_url || 'https://sponsorajobs.com'
  const templateVersion = composition?.template_version || 'v2.0-role-alert'
  const renderedHtml = composition?.rendered_html || subItem?.html_preview || ''

  const queueId = subItem?.queue_id || composition?.queue_id
  const isAlreadySent = subItem?.queue_status === 'SENT' || subItem?.smtp_status === 'SENT'

  const handleSend = async () => {
    if (!queueId) return
    const targetCampId = campaignId || composition?.campaign_id
    if (!targetCampId) return

    if (!window.confirm(`Are you sure you want to verify and send this email to ${recipient}?`)) {
      return
    }

    setSending(true)
    setSendError(null)
    setSendSuccess(null)

    try {
      const res = await api.sendSingleCampaignItem(targetCampId, queueId)
      if (res.success || res.already_sent) {
        setSendSuccess(`Email successfully dispatched to ${recipient}!`)
        if (onItemSent) onItemSent(queueId)
      } else {
        setSendError(res.error || 'Failed to dispatch email')
      }
    } catch (e: any) {
      setSendError(e.message || 'An error occurred while sending email')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '780px', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        <div className="modal-header">
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)' }}>
              ✉ Individual Email Composition Preview
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              True rendered composition directly from the authoritative database record.
            </p>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
            Loading rendered email composition...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header Details Breakdown */}
            <div style={{ background: '#f8fafc', padding: '12px 16px', borderRadius: 'var(--radius-md)', marginBottom: '12px', border: '1px solid var(--border-color)', fontSize: '13px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Recipient: </span><strong>{recipient}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Greeting / Name: </span><strong>{candidateName}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Role: </span><strong>{role}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Company: </span><strong>{company}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Location: </span><strong>{location}</strong></div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Template Version: </span>
                  <span className="badge badge-redirect" style={{ fontSize: '11px', padding: '2px 8px' }}>{templateVersion}</span>
                </div>
              </div>
              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '6px', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Subject: </span>
                <strong style={{ color: '#2563eb' }}>{subject}</strong>
              </div>
              <div style={{ wordBreak: 'break-all' }}>
                <span style={{ color: 'var(--text-muted)' }}>Job Link: </span>
                <a href={jobUrl} target="_blank" rel="noopener noreferrer" style={{ color: '#059669', textDecoration: 'underline', fontWeight: 600 }}>
                  {jobUrl}
                </a>
              </div>
            </div>

            {/* Status Feedback Messages */}
            {sendSuccess && (
              <div style={{ padding: '8px 12px', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', color: '#10b981', fontSize: '12px', fontWeight: 600, marginBottom: '10px' }}>
                ✓ {sendSuccess}
              </div>
            )}
            {sendError && (
              <div style={{ padding: '8px 12px', borderRadius: '4px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid #f43f5e', color: '#f43f5e', fontSize: '12px', fontWeight: 600, marginBottom: '10px' }}>
                ✗ {sendError}
              </div>
            )}

            {/* View Mode Toggle */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <button
                className={`btn ${viewMode === 'html' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '4px 12px', fontSize: '12px' }}
                onClick={() => setViewMode('html')}
              >
                Rendered HTML
              </button>
              <button
                className={`btn ${viewMode === 'text' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '4px 12px', fontSize: '12px' }}
                onClick={() => setViewMode('text')}
              >
                Plain Text
              </button>
            </div>

            {/* Email Content Frame */}
            {viewMode === 'html' ? (
              <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', overflow: 'hidden', height: '420px', background: '#ffffff', marginBottom: '1rem', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.05)' }}>
                <iframe
                  srcDoc={renderedHtml || '<p style="padding:1rem;">Rendering HTML...</p>'}
                  title="Rendered Email Preview"
                  style={{ width: '100%', height: '100%', border: 'none' }}
                />
              </div>
            ) : (
              <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', overflowY: 'auto', height: '420px', background: '#ffffff', padding: '1.25rem', marginBottom: '1rem', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '13px', color: '#1e293b' }}>
                {composition?.rendered_text || 'Plain text unavailable'}
              </div>
            )}

            {/* Footer Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
              <div>
                {queueId && (
                  <button
                    className="btn"
                    style={{
                      background: isAlreadySent ? '#64748b' : '#10b981',
                      color: '#ffffff',
                      border: 'none',
                      fontWeight: 600,
                      fontSize: '13px',
                      padding: '8px 16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                    onClick={handleSend}
                    disabled={sending || isAlreadySent}
                  >
                    {sending ? 'Sending...' : isAlreadySent ? '✓ Already Sent' : '🚀 Verify & Send This Email'}
                  </button>
                )}
              </div>
              <button className="btn btn-secondary" onClick={onClose}>
                Close Preview
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
