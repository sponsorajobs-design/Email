import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<any>(null)
  const [threshold, setThreshold] = useState(70)
  const [dryRun, setDryRun] = useState(true)
  const [testMode, setTestMode] = useState(true)
  const [testEmail, setTestEmail] = useState('')
  const [ratePerMin, setRatePerMin] = useState(10)
  const [autoSync, setAutoSync] = useState(false)
  const [syncInterval, setSyncInterval] = useState(15)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const loadSettings = async () => {
    try {
      const data = await api.getSettings()
      setSettings(data)
      setThreshold(data.match_threshold)
      setDryRun(data.dry_run)
      setTestMode(data.email_test_mode)
      setTestEmail(data.test_email_address || '')
      setRatePerMin(data.email_rate_per_minute)
      if (data.auto_sync_subscribers !== undefined) setAutoSync(data.auto_sync_subscribers)
      if (data.auto_sync_interval_minutes !== undefined) setSyncInterval(data.auto_sync_interval_minutes)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMsg(null)
    try {
      await api.updateSettings({
        match_threshold: threshold,
        dry_run: dryRun,
        email_test_mode: testMode,
        test_email_address: testEmail,
        email_rate_per_minute: ratePerMin,
        auto_sync_subscribers: autoSync,
        auto_sync_interval_minutes: syncInterval
      })
      setMsg('✓ Settings updated successfully!')
      await loadSettings()
    } catch (e: any) {
      setMsg(`✗ Save failed: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ maxWidth: '800px' }}>
      <div className="section-header">
        <div>
          <h2 className="section-title">System Settings & Safety Controls</h2>
          <p className="section-subtitle">
            Configure delivery safeguards, matching weights, and rate limiting.
          </p>
        </div>
      </div>

      {msg && (
        <div style={{
          padding: '12px 18px',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.5rem',
          background: msg.startsWith('✓') ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
          border: `1px solid ${msg.startsWith('✓') ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          color: msg.startsWith('✓') ? '#34d399' : '#fb7185',
          fontSize: '14px',
          fontWeight: 600
        }}>
          {msg}
        </div>
      )}

      <form onSubmit={handleSave}>
        {/* Safety Safeguards Card */}
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '1rem', color: '#f59e0b' }}>
            🛡 Delivery Safety Switches
          </h3>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                style={{ width: '18px', height: '18px' }}
              />
              <div>
                <strong>DRY RUN Mode ({dryRun ? 'ACTIVE' : 'OFF'})</strong>
                <p style={{ fontSize: '12px', color: '#94a3b8' }}>
                  When enabled, matching, queues, and templates execute normally, but zero network packets are sent to SMTP.
                </p>
              </div>
            </label>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={testMode}
                onChange={(e) => setTestMode(e.target.checked)}
                style={{ width: '18px', height: '18px' }}
              />
              <div>
                <strong>EMAIL TEST MODE ({testMode ? 'ACTIVE' : 'OFF'})</strong>
                <p style={{ fontSize: '12px', color: '#94a3b8' }}>
                  Redirects all candidate emails exclusively to the administrator test address below.
                </p>
              </div>
            </label>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Test Recipient Email Address:
            </label>
            <input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              style={{ width: '100%', maxWidth: '400px' }}
              placeholder="e.g. admin-test@sponsorajobs.com"
            />
          </div>
        </div>

        {/* Auto-Sync Subscribers Card */}
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '1rem', color: '#0284c7' }}>
            🔄 Auto-Sync New Subscribers (Supabase Polling)
          </h3>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={autoSync}
                onChange={(e) => setAutoSync(e.target.checked)}
                style={{ width: '18px', height: '18px' }}
              />
              <div>
                <strong>Background Auto-Sync ({autoSync ? 'ACTIVE' : 'DISABLED'})</strong>
                <p style={{ fontSize: '12px', color: '#64748b', margin: '2px 0 0 0' }}>
                  Periodically queries Supabase for newly registered job seekers and pulls them into the local database.
                </p>
              </div>
            </label>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#475569', marginBottom: '6px', fontWeight: 500 }}>
              Auto-Sync Frequency:
            </label>
            <select
              value={syncInterval}
              onChange={(e) => setSyncInterval(Number(e.target.value))}
              style={{ padding: '8px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', background: '#ffffff', color: '#0f172a' }}
            >
              <option value={5}>Every 5 minutes</option>
              <option value={15}>Every 15 minutes (Recommended)</option>
              <option value={30}>Every 30 minutes</option>
              <option value={60}>Every 1 hour</option>
            </select>
          </div>
        </div>

        {/* Algorithm & Delivery Parameters */}
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '1rem' }}>
            ⚙ Engine Parameters
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Default Match Threshold (Points)
              </label>
              <input
                type="number"
                min="50"
                max="100"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Email Sending Rate (Msgs / Minute)
              </label>
              <input
                type="number"
                min="1"
                max="60"
                value={ratePerMin}
                onChange={(e) => setRatePerMin(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* Read-Only Configuration Info */}
          <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem', fontSize: '12px', color: '#94a3b8' }}>
            <div><strong>SMTP Server:</strong> {settings?.smtp_host}:{settings?.smtp_port} (User: {settings?.smtp_username})</div>
            <div style={{ marginTop: '4px' }}><strong>From:</strong> {settings?.from_name} &lt;{settings?.from_email}&gt;</div>
            <div style={{ marginTop: '4px' }}><strong>Supabase Adapter:</strong> {settings?.supabase_configured ? 'Configured' : 'Offline / Mock Adapter'} (Jobs table: {settings?.supabase_job_table}, Subs table: {settings?.supabase_subscriber_table})</div>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  )
}
