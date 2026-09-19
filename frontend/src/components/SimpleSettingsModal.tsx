import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import { DashboardStats, SystemHealth } from '../types'

interface SimpleSettingsModalProps {
  isOpen: boolean
  onClose: () => void
  onUpdate: () => void
  stats: DashboardStats | null
  health: SystemHealth | null
}

export const SimpleSettingsModal: React.FC<SimpleSettingsModalProps> = ({
  isOpen,
  onClose,
  onUpdate,
  stats,
  health
}) => {
  const [testEmail, setTestEmail] = useState(stats?.test_email_address || '')
  const [dryRun, setDryRun] = useState(stats?.dry_run_mode ?? true)
  const [testMode, setTestMode] = useState(stats?.email_test_mode ?? true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (stats) {
      setTestEmail(stats.test_email_address || '')
      setDryRun(stats.dry_run_mode)
      setTestMode(stats.email_test_mode)
    }
  }, [stats])

  if (!isOpen) return null

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      await api.updateSettings({
        test_email_address: testEmail,
        dry_run_mode: dryRun,
        email_test_mode: testMode
      })
      setMessage('Settings updated successfully!')
      onUpdate()
      setTimeout(() => {
        setMessage(null)
        onClose()
      }, 1200)
    } catch (err: any) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '540px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '24px' }}>⚙️</span>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>System & Delivery Settings</h3>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
                Configure email delivery safety switches and your test email.
              </p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '18px', marginTop: '16px' }}>
          {/* SMTP Status Overview */}
          <div style={{
            background: 'var(--bg-primary)',
            padding: '14px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Outbound SMTP Host
              </div>
              <div style={{ fontSize: '14px', fontWeight: 700, marginTop: '2px' }}>
                {health?.smtp_host || 'mail.sponsorajobs.com'}:{health?.smtp_port || 587}
              </div>
            </div>
            <span className="badge" style={{
              background: health?.smtp_configured ? '#ecfdf5' : '#fff1f2',
              color: health?.smtp_configured ? '#059669' : '#e11d48',
              border: `1px solid ${health?.smtp_configured ? '#a7f3d0' : '#fecdd3'}`
            }}>
              {health?.smtp_configured ? '✓ SMTP Configured' : '⚠ Not Connected'}
            </span>
          </div>

          {/* Test Recipient Email */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
              Your Test Email Address
            </label>
            <input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder="e.g. your-email@sponsorajobs.com"
              className="form-control"
              required
            />
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Single test emails and test mode dispatches are safely delivered to this address.
            </p>
          </div>

          {/* Safety Mode Toggles */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <label style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '12px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              background: dryRun ? '#fefce8' : 'var(--bg-secondary)',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                style={{ marginTop: '3px', cursor: 'pointer' }}
              />
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: dryRun ? '#854d0e' : 'var(--text-primary)' }}>
                  Dry Run Mode {dryRun && '(Enabled)'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Simulates full matching and email generation without sending real network packets over SMTP.
                </div>
              </div>
            </label>

            <label style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '12px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              background: testMode ? '#f0f9ff' : 'var(--bg-secondary)',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={testMode}
                onChange={(e) => setTestMode(e.target.checked)}
                style={{ marginTop: '3px', cursor: 'pointer' }}
              />
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: testMode ? '#075985' : 'var(--text-primary)' }}>
                  Test Email Mode {testMode && '(Enabled)'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Redirects outgoing candidate emails to your test address instead of real candidate inboxes.
                </div>
              </div>
            </label>
          </div>

          {message && (
            <div style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              fontWeight: 600,
              background: message.startsWith('Error') ? '#fee2e2' : '#dcfce7',
              color: message.startsWith('Error') ? '#991b1b' : '#166534'
            }}>
              {message}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
