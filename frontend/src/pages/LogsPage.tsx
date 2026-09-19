import React, { useState, useEffect } from 'react'
import { AuditLog } from '../types'
import { api } from '../services/api'

export const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)

  const loadLogs = async () => {
    setLoading(true)
    try {
      const data = await api.getAuditLogs()
      setLogs(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [])

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">Audit Trail & Action Logs</h2>
          <p className="section-subtitle">
            Immutable tracking of synchronization, matching, campaign approvals, and SMTP events.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={loadLogs} disabled={loading}>
          ↻ Refresh Logs
        </button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Details</th>
              <th>Result</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                  {loading ? 'Loading logs...' : 'No audit records recorded yet.'}
                </td>
              </tr>
            ) : (
              logs.map((l) => (
                <tr key={l.id}>
                  <td>#{l.id}</td>
                  <td><strong>{l.actor}</strong></td>
                  <td>
                    <span className="badge badge-unknown" style={{ color: 'var(--accent-blue)' }}>
                      {l.action}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{l.details || '—'}</td>
                  <td>
                    <span className={`badge ${l.result === 'SUCCESS' ? 'badge-live' : 'badge-dead'}`}>
                      {l.result}
                    </span>
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{l.created_at}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
