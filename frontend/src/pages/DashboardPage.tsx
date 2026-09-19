import React, { useState } from 'react'
import { DashboardStats, SystemHealth, Campaign } from '../types'
import { StatsCards } from '../components/StatsCards'
import { FirstRunWizard } from '../components/FirstRunWizard'
import { CampaignModal } from '../components/CampaignModal'
import { api } from '../services/api'

interface DashboardPageProps {
  stats: DashboardStats | null
  health: SystemHealth | null
  campaigns: Campaign[]
  onRefresh: () => void
  onNavigate: (tab: string) => void
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  stats,
  health,
  campaigns,
  onRefresh,
  onNavigate
}) => {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [alertMsg, setAlertMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCampaignModal, setShowCampaignModal] = useState(false)

  const handleAction = async (actionName: string, fn: () => Promise<any>) => {
    setLoadingAction(actionName)
    setAlertMsg(null)
    try {
      const res = await fn()
      setAlertMsg({ type: 'success', text: `✓ ${actionName} completed successfully!` })
      onRefresh()
    } catch (e: any) {
      setAlertMsg({ type: 'error', text: `✗ ${actionName} failed: ${e.message}` })
    } finally {
      setLoadingAction(null)
    }
  }

  const handleCreateCampaign = async (payload: any) => {
    setLoadingAction('Creating Campaign')
    try {
      await api.createCampaign(payload)
      setShowCampaignModal(false)
      setAlertMsg({ type: 'success', text: '✓ Campaign generated and queued in READY status!' })
      onRefresh()
      onNavigate('campaigns')
    } catch (e: any) {
      setAlertMsg({ type: 'error', text: `✗ Failed to stage campaign: ${e.message}` })
    } finally {
      setLoadingAction(null)
    }
  }

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">Operations Dashboard</h2>
          <p className="section-subtitle">
            Local candidate matching, link verification, and controlled email delivery.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={onRefresh}>
            ↻ Refresh Data
          </button>
          <button className="btn btn-primary" onClick={() => setShowCampaignModal(true)} disabled={!!loadingAction}>
            {loadingAction === 'Creating Campaign' ? 'Generating...' : '+ Generate Campaign'}
          </button>
        </div>
      </div>

      {/* Action Banner Message */}
      {alertMsg && (
        <div style={{
          padding: '12px 18px',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.5rem',
          background: alertMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
          border: `1px solid ${alertMsg.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          color: alertMsg.type === 'success' ? '#34d399' : '#fb7185',
          fontSize: '14px',
          fontWeight: 600
        }}>
          {alertMsg.text}
        </div>
      )}

      {/* Primary Action Bar */}
      <div className="action-bar">
        <span style={{ fontSize: '13px', fontWeight: '700', color: '#94a3b8', marginRight: '6px' }}>
          CORE WORKFLOW:
        </span>
        <button
          className="btn btn-secondary"
          onClick={() => handleAction('Sync Subscribers', () => api.syncSubscribers())}
          disabled={loadingAction !== null}
        >
          {loadingAction === 'Sync Subscribers' ? 'Syncing...' : '1. Sync Subscribers'}
        </button>

        <button
          className="btn btn-secondary"
          onClick={() => handleAction('Sync Jobs', () => api.syncJobs())}
          disabled={loadingAction !== null}
        >
          {loadingAction === 'Sync Jobs' ? 'Syncing...' : '2. Sync Jobs'}
        </button>

        <button
          className="btn btn-secondary"
          onClick={() => handleAction('Verify Job Links', () => api.verifyJobLinks(false))}
          disabled={loadingAction !== null}
        >
          {loadingAction === 'Verify Job Links' ? 'Verifying...' : '3. Verify Job Links'}
        </button>

        <button
          className="btn btn-secondary"
          onClick={() => handleAction('Run Matching Engine', () => api.runMatching())}
          disabled={loadingAction !== null}
        >
          {loadingAction === 'Run Matching Engine' ? 'Calculating...' : '4. Run Matching'}
        </button>

        <button
          className="btn btn-primary"
          onClick={() => setShowCampaignModal(true)}
          disabled={loadingAction !== null}
        >
          5. Stage Campaign
        </button>
      </div>

      {/* Health & Diagnostic Wizard */}
      <FirstRunWizard health={health} onRefresh={onRefresh} />

      {/* High-level Metric Tiles */}
      <StatsCards stats={stats} />

      {/* Recent Campaigns Overview */}
      <div style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Recent Staged & Active Campaigns</h3>
          <button className="btn btn-secondary" style={{ fontSize: '12px' }} onClick={() => onNavigate('campaigns')}>
            View All Campaigns &rarr;
          </button>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Campaign Name</th>
                <th>Status</th>
                <th>Batch Size</th>
                <th>Queued</th>
                <th>Sent</th>
                <th>Failed</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                    No campaigns created yet. Click "+ Generate Campaign" to stage your first candidate shortlist batch.
                  </td>
                </tr>
              ) : (
                campaigns.slice(0, 5).map((c) => (
                  <tr key={c.id}>
                    <td>#{c.id}</td>
                    <td><strong>{c.name}</strong></td>
                    <td>
                      <span className={`badge ${
                        c.status === 'READY' ? 'badge-redirect' :
                        c.status === 'SENT' || c.status === 'COMPLETED' ? 'badge-live' :
                        c.status === 'FAILED' || c.status === 'CANCELLED' ? 'badge-dead' : 'badge-unknown'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td>{c.batch_size}</td>
                    <td>{c.total_queued}</td>
                    <td style={{ color: '#10b981', fontWeight: 600 }}>{c.total_sent}</td>
                    <td style={{ color: c.total_failed > 0 ? '#f43f5e' : '#94a3b8' }}>{c.total_failed}</td>
                    <td>{new Date(c.created_at).toLocaleDateString('en-GB')}</td>
                    <td>
                      <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '12px' }} onClick={() => onNavigate('campaigns')}>
                        Manage &rarr;
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <CampaignModal
        isOpen={showCampaignModal}
        onClose={() => setShowCampaignModal(false)}
        onGenerate={handleCreateCampaign}
        loading={loadingAction === 'Creating Campaign'}
      />
    </div>
  )
}
