import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import { Campaign, CampaignSubscriberItem } from '../types'

interface CampaignHistoryPageProps {
  onComposeNew: () => void
}

export const CampaignHistoryPage: React.FC<CampaignHistoryPageProps> = ({ onComposeNew }) => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [subscriberItems, setSubscriberItems] = useState<CampaignSubscriberItem[]>([])
  const [loadingItems, setLoadingItems] = useState(false)
  const [inspectModalOpen, setInspectModalOpen] = useState(false)
  const [previewItem, setPreviewItem] = useState<CampaignSubscriberItem | null>(null)

  const loadCampaigns = async () => {
    setLoading(true)
    try {
      const list = await api.getCampaigns()
      setCampaigns(list)
    } catch (err) {
      console.error('Failed to load campaigns:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCampaigns()
  }, [])

  const handleInspectCampaign = async (c: Campaign) => {
    setSelectedCampaign(c)
    setInspectModalOpen(true)
    setLoadingItems(true)
    try {
      const items = await api.getCampaignSubscribers(c.id, 100)
      setSubscriberItems(items)
    } catch (err) {
      console.error('Failed to load campaign items:', err)
    } finally {
      setLoadingItems(false)
    }
  }

  return (
    <div className="campaign-history-container">
      {/* Header */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            📊 Sent Campaigns & History
          </h1>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '14px' }}>
            Track all delivered candidate job alerts, embedded links, and recipient delivery statistics.
          </p>
        </div>

        <button type="button" className="btn btn-primary" onClick={onComposeNew}>
          ✉️ Compose New Campaign
        </button>
      </div>

      {/* Campaigns Table Card */}
      <div className="compose-card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading campaign history...
          </div>
        ) : campaigns.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📭</div>
            <div style={{ fontSize: '16px', fontWeight: 700 }}>No Campaigns Sent Yet</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Launch your first email alert to see real-time delivery stats here.
            </div>
            <button
              type="button"
              className="btn btn-primary"
              style={{ marginTop: '16px' }}
              onClick={onComposeNew}
            >
              ✉️ Create First Campaign
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--bg-primary)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '12px 16px', width: '60px' }}>ID</th>
                  <th style={{ padding: '12px 16px' }}>Campaign & Job Name</th>
                  <th style={{ padding: '12px 16px' }}>Embedded Link</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                  <th style={{ padding: '12px 16px' }}>Recipients</th>
                  <th style={{ padding: '12px 16px' }}>Date</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => {
                  const isCompleted = c.status === 'COMPLETED' || c.total_sent > 0
                  return (
                    <tr key={c.id} style={{ borderBottom: '1px solid var(--border-color)' }} className="table-row-hover">
                      <td style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--text-muted)' }}>
                        #{c.id}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '14px' }}>
                          {c.name}
                        </div>
                        {c.notes && (
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                            {c.notes}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '12px 16px', maxWidth: '240px' }}>
                        {c.notes && c.notes.includes('Link: ') ? (
                          <a
                            href={c.notes.split('Link: ')[1].split(' ')[0]}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: 'var(--accent-blue)', textDecoration: 'none', wordBreak: 'break-all', fontSize: '12px' }}
                          >
                            🔗 {c.notes.split('Link: ')[1].split(' ')[0]}
                          </a>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Embedded in emails</span>
                        )}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span className="badge" style={{
                          background: isCompleted ? '#ecfdf5' : '#fffbeb',
                          color: isCompleted ? '#059669' : '#b45309',
                          border: `1px solid ${isCompleted ? '#a7f3d0' : '#fde68a'}`
                        }}>
                          {c.status || 'COMPLETED'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 700 }}>
                          {c.total_sent} sent
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {c.total_queued || c.total_candidates} total queued
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '12px' }}>
                        {c.created_at ? new Date(c.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleInspectCampaign(c)}
                        >
                          Inspect Recipients
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inspect Campaign Modal */}
      {inspectModalOpen && selectedCampaign && (
        <div className="modal-overlay" onClick={() => setInspectModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '850px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800 }}>
                  Campaign #{selectedCampaign.id}: {selectedCampaign.name}
                </h3>
                <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
                  Delivery breakdown: {selectedCampaign.total_sent} sent, {selectedCampaign.total_failed || 0} failed.
                </p>
              </div>
              <button className="btn-close" onClick={() => setInspectModalOpen(false)}>&times;</button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', marginTop: '16px', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
              {loadingItems ? (
                <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  Loading recipient logs...
                </div>
              ) : subscriberItems.length === 0 ? (
                <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No individual recipient items found.
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-primary)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                      <th style={{ padding: '10px 14px' }}>Recipient</th>
                      <th style={{ padding: '10px 14px' }}>Job Alert Title</th>
                      <th style={{ padding: '10px 14px' }}>Embedded Link</th>
                      <th style={{ padding: '10px 14px' }}>Status</th>
                      <th style={{ padding: '10px 14px' }}>Delivery Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subscriberItems.map(item => (
                      <tr key={item.queue_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ fontWeight: 600 }}>{item.subscriber_name}</div>
                          <div style={{ fontSize: '12px', color: 'var(--accent-blue)' }}>{item.subscriber_email}</div>
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--text-primary)' }}>
                          {item.job_title}
                        </td>
                        <td style={{ padding: '10px 14px', maxWidth: '200px' }}>
                          <a
                            href={item.job_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontSize: '12px' }}
                          >
                            🔗 {item.job_url}
                          </a>
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <span className="badge" style={{
                            background: item.queue_status === 'SENT' ? '#ecfdf5' : '#fffbeb',
                            color: item.queue_status === 'SENT' ? '#059669' : '#b45309'
                          }}>
                            {item.queue_status}
                          </span>
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--text-muted)', fontSize: '12px' }}>
                          {item.sent_at ? new Date(item.sent_at).toLocaleString() : 'Queued'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '14px' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setInspectModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
