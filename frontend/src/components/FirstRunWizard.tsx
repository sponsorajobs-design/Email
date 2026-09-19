import React, { useState, useEffect } from 'react'
import { SystemHealth } from '../types'
import { api } from '../services/api'

interface FirstRunWizardProps {
  health: SystemHealth | null
  onRefresh: () => void
}

export const FirstRunWizard: React.FC<FirstRunWizardProps> = ({ health, onRefresh }) => {
  const [supaTest, setSupaTest] = useState<any>(null)
  const [testingSupa, setTestingSupa] = useState(false)
  const [sendingTest, setSendingTest] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [testEmailAddr, setTestEmailAddr] = useState('admin-test@sponsorajobs.com')

  const runSupabaseTest = async () => {
    setTestingSupa(true)
    try {
      const res = await api.testSupabaseConnection()
      setSupaTest(res)
    } catch (e: any) {
      setSupaTest({ status: 'error', message: e.message })
    } finally {
      setTestingSupa(false)
    }
  }

  const handleSendTestEmail = async () => {
    setSendingTest(true)
    setTestResult(null)
    try {
      const res = await api.sendTestEmail({
        recipient: testEmailAddr,
        candidate_name: 'Priya Sharma (Test)',
        job_title: 'Senior Data Analyst',
        company_name: 'KPMG UK',
        location: 'London, UK',
        experience: '3+ years',
        match_reasons: 'Preferred role matches Data Analyst\nSQL & Power BI match requirements',
        application_url: 'https://sponsorajobs.com/jobs/sample'
      })
      setTestResult(res)
    } catch (e: any) {
      setTestResult({ message: 'Failed to trigger test email', error: e.message })
    } finally {
      setSendingTest(false)
    }
  }

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid var(--border-color)',
      borderRadius: 'var(--radius-lg)',
      padding: '1.5rem',
      marginBottom: '2rem',
      boxShadow: 'var(--shadow-sm)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)' }}>
            System Setup & Readiness Diagnostic
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Verify local database, read-only Supabase connectivity, and SMTP safeguards.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh}>
          Refresh Diagnostics
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
        {/* Local DB */}
        <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{ color: '#059669', fontWeight: 'bold' }}>✓</span>
            <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>Local SQLite Database</strong>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Status: <span style={{ color: '#059669', fontWeight: 600 }}>{health?.database === 'ok' ? 'Connected & Ready' : health?.database}</span>
          </p>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Path: data/sponsorajobs_local.db
          </p>
        </div>

        {/* Supabase */}
        <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: health?.supabase_configured ? '#059669' : '#d97706', fontWeight: 'bold' }}>
                {health?.supabase_configured ? '✓' : 'ℹ'}
              </span>
              <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>Production Supabase</strong>
            </div>
            <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={runSupabaseTest} disabled={testingSupa}>
              {testingSupa ? 'Testing...' : 'Test Read-Only'}
            </button>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Mode: <span style={{ color: health?.supabase_configured ? '#059669' : '#d97706', fontWeight: 600 }}>
              {health?.supabase_configured ? 'Read-Only Connected' : 'Offline / Mock Adapter Mode'}
            </span>
          </p>
          {supaTest && (
            <p style={{ fontSize: '11px', color: supaTest.connected ? '#059669' : '#d97706', marginTop: '4px' }}>
              {supaTest.message}
            </p>
          )}
        </div>

        {/* SMTP */}
        <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{ color: health?.smtp_configured ? '#059669' : '#d97706', fontWeight: 'bold' }}>
              {health?.smtp_configured ? '✓' : 'ℹ'}
            </span>
            <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>SMTP Host (Port 587)</strong>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Server: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{health?.smtp_host}:{health?.smtp_port}</span> (STARTTLS)
          </p>
          <div style={{ marginTop: '8px', display: 'flex', gap: '6px' }}>
            <input
              type="email"
              value={testEmailAddr}
              onChange={(e) => setTestEmailAddr(e.target.value)}
              placeholder="Test recipient email"
              style={{ fontSize: '12px', padding: '4px 8px', flex: 1 }}
            />
            <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={handleSendTestEmail} disabled={sendingTest}>
              {sendingTest ? 'Sending...' : 'Send Test'}
            </button>
          </div>
          {testResult && (
            <p style={{ fontSize: '11px', color: testResult.result?.success ? '#059669' : '#e11d48', marginTop: '4px' }}>
              {testResult.result?.success ? `✓ Test email processed in mode: ${testResult.result.mode}` : testResult.message}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
