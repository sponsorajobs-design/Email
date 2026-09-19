import React, { useState, useEffect } from 'react'
import {
  Campaign,
  CampaignSubscriberItem,
  CampaignCompositionDetail,
  DecisionTrace
} from '../types'
import { CampaignModal } from '../components/CampaignModal'
import { EmailPreviewModal } from '../components/EmailPreviewModal'
import { DecisionTraceModal } from '../components/DecisionTraceModal'
import { api } from '../services/api'

export const CampaignsPage: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [subscriberItems, setSubscriberItems] = useState<CampaignSubscriberItem[]>([])
  const [searchFilter, setSearchFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [domainFilter, setDomainFilter] = useState('ALL')

  // Multi-select & single sending state
  const [selectedQueueIds, setSelectedQueueIds] = useState<number[]>([])
  const [sendingSelected, setSendingSelected] = useState(false)
  const [sendingSingleId, setSendingSingleId] = useState<number | null>(null)

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedSubscriberItem, setSelectedSubscriberItem] = useState<CampaignSubscriberItem | null>(null)
  const [currentComposition, setCurrentComposition] = useState<CampaignCompositionDetail | null>(null)
  const [currentTrace, setCurrentTrace] = useState<DecisionTrace | null>(null)
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [traceModalOpen, setTraceModalOpen] = useState(false)
  const [modalLoading, setModalLoading] = useState(false)

  const [actionLoading, setActionLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const loadCampaigns = async (autoSelectId?: number) => {
    try {
      const data = await api.getCampaigns()
      setCampaigns(data)
      if (data.length > 0) {
        if (autoSelectId) {
          const target = data.find((c) => c.id === autoSelectId) || data[0]
          selectCampaign(target)
        } else if (!selectedCampaign) {
          selectCampaign(data[0])
        }
      }
    } catch (e) {
      console.error('Failed to load campaigns:', e)
    }
  }

  const selectCampaign = async (c: Campaign) => {
    setSelectedCampaign(c)
    setSelectedQueueIds([])
    setStatusMsg(null)
    try {
      const items = await api.getCampaignSubscribers(c.id, 300)
      setSubscriberItems(items)
    } catch (e) {
      console.error('Failed to load campaign subscribers:', e)
    }
  }

  useEffect(() => {
    loadCampaigns()
  }, [])

  const handleCreate = async (payload: any) => {
    setActionLoading(true)
    try {
      const c = await api.createCampaign(payload)
      setShowCreateModal(false)
      await loadCampaigns(c.id)
      setStatusMsg({
        type: 'success',
        text: `Campaign "${c.name}" generated! ${c.total_queued} individualized emails ready for review.`
      })
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `Failed to create campaign: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleDispatch = async () => {
    if (!selectedCampaign) return
    if (!window.confirm(`CONFIRMATION: Dispatch Campaign #${selectedCampaign.id} ("${selectedCampaign.name}")? This will send ${selectedCampaign.total_queued} queued emails via SMTP.`)) {
      return
    }

    setActionLoading(true)
    try {
      const res = await api.dispatchCampaign(selectedCampaign.id, selectedCampaign.batch_size)
      setStatusMsg({
        type: 'success',
        text: `Dispatch executed: ${res.sent || 0} sent, ${res.failed || 0} failed. Status: ${res.campaign_status}`
      })
      await loadCampaigns(selectedCampaign.id)
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `Dispatch failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!selectedCampaign) return
    if (!window.confirm(`Cancel Campaign #${selectedCampaign.id}? Any pending queue items will be cancelled.`)) return
    setActionLoading(true)
    try {
      await api.cancelCampaign(selectedCampaign.id)
      setStatusMsg({ type: 'success', text: `Campaign #${selectedCampaign.id} has been cancelled.` })
      await loadCampaigns(selectedCampaign.id)
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `Cancel failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const openPreview = async (item: CampaignSubscriberItem) => {
    setSelectedSubscriberItem(item)
    setPreviewModalOpen(true)
    if (!selectedCampaign || !item.composition_id) return

    setModalLoading(true)
    try {
      const comp = await api.getCampaignComposition(selectedCampaign.id, item.composition_id)
      setCurrentComposition(comp)
    } catch (e) {
      console.error('Failed to load composition preview:', e)
    } finally {
      setModalLoading(false)
    }
  }

  const openDecisionTrace = async (item: CampaignSubscriberItem) => {
    setSelectedSubscriberItem(item)
    setTraceModalOpen(true)
    if (!selectedCampaign || !item.composition_id) return

    setModalLoading(true)
    try {
      const comp = await api.getCampaignComposition(selectedCampaign.id, item.composition_id)
      setCurrentComposition(comp)
      setCurrentTrace(comp.decision_trace || null)
    } catch (e) {
      console.error('Failed to load decision trace:', e)
    } finally {
      setModalLoading(false)
    }
  }

  const filteredItems = subscriberItems.filter((item) => {
    const matchesSearch =
      item.subscriber_email.toLowerCase().includes(searchFilter.toLowerCase()) ||
      item.subscriber_name.toLowerCase().includes(searchFilter.toLowerCase()) ||
      item.job_title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      item.company_name.toLowerCase().includes(searchFilter.toLowerCase())

    if (!matchesSearch) return false
    if (statusFilter !== 'ALL' && item.queue_status !== statusFilter) return false

    if (domainFilter !== 'ALL') {
      const emailLower = item.subscriber_email.toLowerCase()
      if (domainFilter === 'gmail' && !emailLower.includes('@gmail.')) return false
      if (domainFilter === 'yahoo' && !emailLower.includes('@yahoo.')) return false
      if (domainFilter === 'outlook' && !emailLower.includes('@outlook.') && !emailLower.includes('@hotmail.')) return false
      if (domainFilter === 'other' && (emailLower.includes('@gmail.') || emailLower.includes('@yahoo.') || emailLower.includes('@outlook.') || emailLower.includes('@hotmail.'))) return false
    }

    return true
  })

  const selectableItems = filteredItems.filter((i) => i.queue_status !== 'SENT')
  const allFilteredSelected = selectableItems.length > 0 && selectableItems.every((i) => selectedQueueIds.includes(i.queue_id))

  const toggleSelectQueueId = (queueId: number) => {
    setSelectedQueueIds((prev) =>
      prev.includes(queueId) ? prev.filter((id) => id !== queueId) : [...prev, queueId]
    )
  }

  const toggleSelectAll = () => {
    if (selectableItems.length === 0) return
    if (allFilteredSelected) {
      const selectableIds = selectableItems.map((i) => i.queue_id)
      setSelectedQueueIds((prev) => prev.filter((id) => !selectableIds.includes(id)))
    } else {
      const selectableIds = selectableItems.map((i) => i.queue_id)
      setSelectedQueueIds((prev) => Array.from(new Set([...prev, ...selectableIds])))
    }
  }

  const handleSendSingleRow = async (item: CampaignSubscriberItem) => {
    if (!selectedCampaign) return
    if (!window.confirm(`Verify & send email to ${item.subscriber_email} for "${item.job_title}"?`)) {
      return
    }
    setSendingSingleId(item.queue_id)
    try {
      const res = await api.sendSingleCampaignItem(selectedCampaign.id, item.queue_id)
      if (res.success || res.already_sent) {
        setStatusMsg({ type: 'success', text: `Email sent to ${item.subscriber_email}!` })
        setSubscriberItems((prev) =>
          prev.map((i) =>
            i.queue_id === item.queue_id
              ? { ...i, queue_status: 'SENT', smtp_status: 'SENT', sent_at: new Date().toISOString() }
              : i
          )
        )
        setSelectedQueueIds((prev) => prev.filter((id) => id !== item.queue_id))
      } else {
        setStatusMsg({ type: 'error', text: `Send failed: ${res.error || 'Unknown error'}` })
      }
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `Send failed: ${e.message}` })
    } finally {
      setSendingSingleId(null)
    }
  }

  const handleSendSelected = async () => {
    if (!selectedCampaign || selectedQueueIds.length === 0) return
    if (!window.confirm(`Are you sure you want to verify and send ${selectedQueueIds.length} selected email(s)?`)) {
      return
    }
    setSendingSelected(true)
    try {
      const res = await api.sendSelectedCampaignItems(selectedCampaign.id, selectedQueueIds)
      setStatusMsg({
        type: 'success',
        text: `Sent ${res.sent || 0} of ${res.total_selected} selected emails (${res.failed || 0} failed).`
      })
      const sentIds = new Set(
        (res.results || [])
          .filter((r: any) => r.success || r.already_sent)
          .map((r: any) => r.queue_id)
      )
      setSubscriberItems((prev) =>
        prev.map((i) =>
          sentIds.has(i.queue_id)
            ? { ...i, queue_status: 'SENT', smtp_status: 'SENT', sent_at: new Date().toISOString() }
            : i
        )
      )
      setSelectedQueueIds([])
      const updatedCamp = await api.getCampaign(selectedCampaign.id)
      setSelectedCampaign(updatedCamp)
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `Failed to send selected emails: ${e.message}` })
    } finally {
      setSendingSelected(false)
    }
  }

  const handleItemSentFromModal = (queueId: number) => {
    setSubscriberItems((prev) =>
      prev.map((i) =>
        i.queue_id === queueId
          ? { ...i, queue_status: 'SENT', smtp_status: 'SENT', sent_at: new Date().toISOString() }
          : i
      )
    )
    setSelectedQueueIds((prev) => prev.filter((id) => id !== queueId))
  }

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">Campaign Generation & Email Control Center</h2>
          <p className="section-subtitle">
            Generate role-based job alert emails, inspect exact rendered compositions and decision traces, and dispatch safely.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)} disabled={actionLoading}>
          {actionLoading ? 'Generating...' : '+ Generate New Campaign'}
        </button>
      </div>

      {statusMsg && (
        <div style={{
          padding: '12px 18px',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.5rem',
          background: statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
          border: `1px solid ${statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          color: statusMsg.type === 'success' ? '#34d399' : '#fb7185',
          fontSize: '14px',
          fontWeight: 600
        }}>
          {statusMsg.text}
        </div>
      )}

      {/* Campaign Selection Pills */}
      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', marginBottom: '1.5rem', paddingBottom: '4px' }}>
        {campaigns.map((c) => (
          <button
            key={c.id}
            className={`btn ${selectedCampaign?.id === c.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => selectCampaign(c)}
            style={{ fontSize: '13px', whiteSpace: 'nowrap' }}
          >
            #{c.id} {c.name}
            <span style={{
              marginLeft: '8px',
              padding: '2px 6px',
              borderRadius: '4px',
              background: 'rgba(255,255,255,0.2)',
              fontSize: '11px'
            }}>
              {c.status}
            </span>
          </button>
        ))}
      </div>

      {selectedCampaign && (
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '1.5rem', marginBottom: '2rem' }}>
          {/* Header & Main Actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h3 style={{ fontSize: '22px', fontWeight: '800', color: '#f8fafc' }}>
                  {selectedCampaign.name}
                </h3>
                <span className={`badge ${
                  selectedCampaign.status === 'READY' || selectedCampaign.status === 'GENERATED' ? 'badge-redirect' :
                  selectedCampaign.status === 'COMPLETED' ? 'badge-live' :
                  selectedCampaign.status === 'DISPATCHING' || selectedCampaign.status === 'SENDING' ? 'badge-redirect' :
                  selectedCampaign.status === 'CANCELLED' || selectedCampaign.status === 'FAILED' ? 'badge-dead' : 'badge-unknown'
                }`}>
                  {selectedCampaign.status}
                </span>
              </div>
              <p style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>
                Created: {new Date(selectedCampaign.created_at).toLocaleString('en-GB')} {selectedCampaign.notes ? `• ${selectedCampaign.notes}` : ''}
              </p>
            </div>

            {/* Stage-Gated Actions */}
            <div style={{ display: 'flex', gap: '10px' }}>
              {(selectedCampaign.status === 'READY' || selectedCampaign.status === 'APPROVED' || selectedCampaign.status === 'GENERATED') && (
                <button className="btn btn-success" onClick={handleDispatch} disabled={actionLoading}>
                  {actionLoading ? 'Dispatching...' : '🚀 DISPATCH CAMPAIGN'}
                </button>
              )}

              {selectedCampaign.status !== 'COMPLETED' && selectedCampaign.status !== 'CANCELLED' && (
                <button className="btn btn-danger" onClick={handleCancel} disabled={actionLoading}>
                  Cancel Campaign
                </button>
              )}
            </div>
          </div>

          {/* Section 7 Detailed Metric Breakdown Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', marginBottom: '1.5rem' }}>
            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Evaluated</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#38bdf8' }}>
                {selectedCampaign.total_candidates}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Subscribers</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Generated</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#818cf8' }}>
                {selectedCampaign.emails_generated ?? selectedCampaign.total_matches}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Compositions</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Queued</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#f59e0b' }}>
                {selectedCampaign.total_queued}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Queue records</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Sent</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#10b981' }}>
                {selectedCampaign.total_sent}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Delivered</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Failed</div>
              <div className="stat-value" style={{ fontSize: '20px', color: selectedCampaign.total_failed > 0 ? '#f43f5e' : '#94a3b8' }}>
                {selectedCampaign.total_failed}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Delivery errors</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Skipped Total</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#94a3b8' }}>
                {selectedCampaign.total_skipped}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Ineligible</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>No Eligible Job</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#64748b' }}>
                {selectedCampaign.no_eligible_job_count ?? 0}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>0 relevant jobs</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Freq Blocked</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#f59e0b' }}>
                {selectedCampaign.frequency_blocked_count ?? 0}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Daily/Weekly</div>
            </div>

            <div className="stat-card" style={{ padding: '12px' }}>
              <div className="stat-label" style={{ fontSize: '11px' }}>Deduplicated</div>
              <div className="stat-value" style={{ fontSize: '20px', color: '#a855f7' }}>
                {selectedCampaign.deduplicated_count ?? 0}
              </div>
              <div className="stat-subtext" style={{ fontSize: '11px' }}>Already burned</div>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div style={{ display: 'flex', gap: '12px', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search candidate, email, role, or company..."
              style={{ flex: 1, minWidth: '240px' }}
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ width: '160px' }}
            >
              <option value="ALL">All Queue Statuses</option>
              <option value="PENDING">PENDING</option>
              <option value="SENDING">SENDING</option>
              <option value="SENT">SENT</option>
              <option value="FAILED">FAILED</option>
              <option value="REQUIRES_RECONCILIATION">REQUIRES_RECONCILIATION</option>
            </select>
            <select
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value)}
              style={{ width: '190px' }}
              title="Filter by Email Provider Domain"
            >
              <option value="ALL">🌐 All Email Domains</option>
              <option value="gmail">✉ Gmail (@gmail.com)</option>
              <option value="yahoo">✉ Yahoo (@yahoo.*)</option>
              <option value="outlook">✉ Outlook / Hotmail</option>
              <option value="other">🏢 Corporate / Other Domains</option>
            </select>
          </div>

          {/* Multi-Selection Sticky / Floating Action Bar */}
          {selectedQueueIds.length > 0 && (
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 18px',
              background: '#0f172a',
              border: '1px solid #3b82f6',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '1rem',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '16px' }}>✉</span>
                <span style={{ color: '#f8fafc', fontWeight: 700, fontSize: '14px' }}>
                  {selectedQueueIds.length} candidate email{selectedQueueIds.length > 1 ? 's' : ''} selected
                </span>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn"
                  style={{
                    background: '#10b981',
                    color: '#ffffff',
                    border: 'none',
                    fontWeight: 700,
                    fontSize: '13px',
                    padding: '6px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                  onClick={handleSendSelected}
                  disabled={sendingSelected}
                >
                  {sendingSelected ? 'Sending Selected...' : `🚀 Verify & Send Selected (${selectedQueueIds.length})`}
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                  onClick={() => setSelectedQueueIds([])}
                >
                  Clear Selection
                </button>
              </div>
            </div>
          )}

          {/* Section 7 Subscriber Compositions Table */}
          <div className="table-container" style={{ marginBottom: 0 }}>
            <table>
              <thead>
                <tr>
                  <th style={{ width: '40px', textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      checked={allFilteredSelected}
                      onChange={toggleSelectAll}
                      title={allFilteredSelected ? "Deselect all" : "Select all eligible"}
                      style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                    />
                  </th>
                  <th>Subscriber</th>
                  <th>Selected Role</th>
                  <th>Selected Job</th>
                  <th>Job URL</th>
                  <th>Email Subject</th>
                  <th>Queue Status</th>
                  <th>SMTP Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                      No subscriber email rows matching the current filter.
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => (
                    <tr key={item.queue_id} style={{ background: selectedQueueIds.includes(item.queue_id) ? 'rgba(59, 130, 246, 0.08)' : undefined }}>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={selectedQueueIds.includes(item.queue_id)}
                          onChange={() => toggleSelectQueueId(item.queue_id)}
                          disabled={item.queue_status === 'SENT'}
                          style={{ cursor: item.queue_status === 'SENT' ? 'not-allowed' : 'pointer', width: '16px', height: '16px' }}
                        />
                      </td>
                      <td>
                        <strong>{item.subscriber_name && !/\d/.test(item.subscriber_name) && !['candidate', 'subscriber', 'applicant', 'user'].includes(item.subscriber_name.toLowerCase()) ? item.subscriber_name : 'Candidate'}</strong>
                        <div style={{ fontSize: '12px', color: '#94a3b8' }}>{item.subscriber_email}</div>
                        <div style={{ fontSize: '11px', color: '#64748b' }}>Country: {item.country_code || 'ALL'} • {item.frequency || 'DAILY'}</div>
                      </td>
                      <td style={{ maxWidth: '220px' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {(item.preferred_roles || 'All Roles').split(',').map((r, rIdx) => (
                            <span key={rIdx} style={{
                              background: 'rgba(56, 189, 248, 0.12)',
                              color: '#38bdf8',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 500,
                              display: 'inline-block'
                            }}>
                              {r.trim()}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <strong>{item.job_title}</strong>
                        <div style={{ fontSize: '12px', color: '#38bdf8' }}>{item.company_name}</div>
                        <div style={{ fontSize: '11px', color: '#64748b' }}>{item.location || 'United Kingdom'}</div>
                      </td>
                      <td style={{ maxWidth: '180px' }}>
                        <a
                          href={item.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#2563eb', textDecoration: 'underline', fontSize: '12px', wordBreak: 'break-all' }}
                        >
                          {item.job_url}
                        </a>
                      </td>
                      <td style={{ maxWidth: '200px', fontSize: '12px' }}>
                        <span style={{ color: '#e2e8f0' }}>{item.email_subject}</span>
                      </td>
                      <td>
                        <span className={`badge ${
                          item.queue_status === 'SENT' ? 'badge-live' :
                          item.queue_status === 'PENDING' ? 'badge-unknown' :
                          item.queue_status === 'SENDING' ? 'badge-redirect' :
                          item.queue_status === 'FAILED' ? 'badge-dead' : 'badge-unknown'
                        }`}>
                          {item.queue_status}
                        </span>
                      </td>
                      <td>
                        {item.smtp_status === 'SENT' ? (
                          <span style={{ color: '#10b981', fontWeight: 600, fontSize: '12px' }}>
                            ✓ SENT
                            {item.sent_at && <div style={{ fontSize: '10px', color: '#64748b' }}>{new Date(item.sent_at).toLocaleTimeString('en-GB')}</div>}
                          </span>
                        ) : item.smtp_status === 'FAILED' ? (
                          <span style={{ color: '#f43f5e', fontWeight: 600, fontSize: '12px' }}>
                            ✗ FAILED
                            {item.error_message && <div style={{ fontSize: '10px', color: '#f43f5e', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.error_message}</div>}
                          </span>
                        ) : (
                          <span style={{ color: '#64748b', fontSize: '12px' }}>Queued</span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            onClick={() => openPreview(item)}
                          >
                            👁 Preview
                          </button>
                          <button
                            className="btn"
                            style={{
                              padding: '4px 8px',
                              fontSize: '11px',
                              background: item.queue_status === 'SENT' ? '#334155' : '#10b981',
                              color: '#ffffff',
                              border: 'none',
                              cursor: item.queue_status === 'SENT' ? 'default' : 'pointer'
                            }}
                            onClick={() => handleSendSingleRow(item)}
                            disabled={item.queue_status === 'SENT' || sendingSingleId === item.queue_id}
                            title={item.queue_status === 'SENT' ? 'Email already sent' : 'Verify & Send this email now'}
                          >
                            {sendingSingleId === item.queue_id ? '...' : item.queue_status === 'SENT' ? '✓ Sent' : '🚀 Send'}
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '11px', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}
                            onClick={() => openDecisionTrace(item)}
                          >
                            🎯 Why
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <CampaignModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onGenerate={handleCreate}
        loading={actionLoading}
      />

      <EmailPreviewModal
        composition={currentComposition}
        item={selectedSubscriberItem}
        campaignId={selectedCampaign?.id}
        loading={modalLoading}
        onItemSent={handleItemSentFromModal}
        onClose={() => {
          setPreviewModalOpen(false)
          setSelectedSubscriberItem(null)
          setCurrentComposition(null)
        }}
      />

      <DecisionTraceModal
        item={selectedSubscriberItem}
        trace={currentTrace}
        loading={modalLoading}
        onClose={() => {
          setTraceModalOpen(false)
          setSelectedSubscriberItem(null)
          setCurrentTrace(null)
        }}
      />
    </div>
  )
}
