import React, { useState, useEffect } from 'react'
import { Job } from '../types'
import { api } from '../services/api'

export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [verifying, setVerifying] = useState(false)
  const [loading, setLoading] = useState(false)

  const loadJobs = async (status?: string) => {
    setLoading(true)
    try {
      const data = await api.getJobs(status)
      setJobs(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs(statusFilter)
  }, [statusFilter])

  const handleVerify = async (force: boolean) => {
    setVerifying(true)
    try {
      await api.verifyJobLinks(force)
      await loadJobs(statusFilter)
    } catch (e) {
      console.error(e)
    } finally {
      setVerifying(false)
    }
  }

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">Live Jobs & URL Verification</h2>
          <p className="section-subtitle">
            Local snapshot of job listings and proactive HTTP link verification checks.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={() => handleVerify(false)} disabled={verifying}>
            {verifying ? 'Verifying URLs...' : 'Verify Pending Links'}
          </button>
          <button className="btn btn-primary" onClick={() => handleVerify(true)} disabled={verifying}>
            Force Re-Verify All
          </button>
        </div>
      </div>

      <div className="action-bar">
        <span style={{ fontSize: '13px', color: '#94a3b8', marginRight: '6px' }}>Filter by URL Status:</span>
        {['', 'LIVE', 'DEAD', 'REDIRECTED', 'UNKNOWN'].map((s) => (
          <button
            key={s}
            className={`btn ${statusFilter === s ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '5px 12px' }}
            onClick={() => setStatusFilter(s)}
          >
            {s === '' ? 'All Jobs' : s}
          </button>
        ))}
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Job Title</th>
              <th>Company</th>
              <th>Location</th>
              <th>URL Status</th>
              <th>HTTP Code</th>
              <th>SponsorAJobs Listing</th>
              <th>Verified At</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                  {loading ? 'Loading jobs...' : 'No jobs found for this filter.'}
                </td>
              </tr>
            ) : (
              jobs.map((j) => (
                <tr key={j.id}>
                  <td>#{j.id}</td>
                  <td><strong>{j.title}</strong></td>
                  <td>{j.company}</td>
                  <td>{j.location || 'UK'}</td>
                  <td>
                    <span className={`badge ${
                      j.verification_status === 'LIVE' ? 'badge-live' :
                      j.verification_status === 'DEAD' ? 'badge-dead' :
                      j.verification_status === 'REDIRECTED' ? 'badge-redirect' : 'badge-unknown'
                    }`}>
                      {j.verification_status}
                    </span>
                  </td>
                  <td>
                    {j.verification_http_status ? (
                      <span style={{ color: j.verification_http_status < 400 ? '#10b981' : '#f43f5e', fontWeight: 600 }}>
                        {j.verification_http_status}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td style={{ minWidth: '180px' }}>
                    <a
                      href={`https://sponsorajobs.com/job/${j.source_job_id || j.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontSize: '12px',
                        color: 'var(--primary)',
                        textDecoration: 'none',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontWeight: 600,
                        background: '#eff6ff',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        border: '1px solid #bfdbfe'
                      }}
                    >
                      <span>🌐 View on SponsorAJobs</span>
                      <span>↗</span>
                    </a>
                  </td>
                  <td style={{ fontSize: '12px', color: '#94a3b8' }}>
                    {j.verified_at ? new Date(j.verified_at).toLocaleTimeString('en-GB') : 'Not checked'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
