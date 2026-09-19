import React, { useState, useEffect } from 'react'
import { EmailQueueItem } from '../types'
import { api } from '../services/api'

export const QueuePage: React.FC = () => {
  const [queue, setQueue] = useState<EmailQueueItem[]>([])
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const loadQueue = async (status?: string) => {
    setLoading(true)
    try {
      const data = await api.getEmailQueue(status)
      setQueue(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadQueue(filterStatus)
    const interval = setInterval(() => loadQueue(filterStatus), 5000)
    return () => clearInterval(interval)
  }, [filterStatus])

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">Outbound Email Queue Monitor</h2>
          <p className="section-subtitle">
            Real-time delivery progress, retry counts, and message delivery audit receipts.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={() => loadQueue(filterStatus)} disabled={loading}>
          ↻ Refresh Queue
        </button>
      </div>

      <div className="action-bar">
        <span style={{ fontSize: '13px', color: '#94a3b8', marginRight: '6px' }}>Status Filter:</span>
        {['', 'PENDING', 'SENDING', 'SENT', 'FAILED', 'CANCELLED'].map((s) => (
          <button
            key={s}
            className={`btn ${filterStatus === s ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '5px 12px' }}
            onClick={() => setFilterStatus(s)}
          >
            {s === '' ? 'All Statuses' : s}
          </button>
        ))}
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Campaign</th>
              <th>Recipient</th>
              <th>Candidate Name</th>
              <th>Subject Line</th>
              <th>Status</th>
              <th>Attempts</th>
              <th>Sent At</th>
              <th>Diagnostic / Message-ID</th>
            </tr>
          </thead>
          <tbody>
            {queue.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                  {loading ? 'Loading queue...' : 'No queue items found.'}
                </td>
              </tr>
            ) : (
              queue.map((item) => (
                <tr key={item.id}>
                  <td>#{item.id}</td>
                  <td>#{item.campaign_id}</td>
                  <td><strong>{item.recipient}</strong></td>
                  <td>{item.candidate_name || 'Candidate'}</td>
                  <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.subject}
                  </td>
                  <td>
                    <span className={`badge ${
                      item.status === 'SENT' ? 'badge-live' :
                      item.status === 'FAILED' || item.status === 'CANCELLED' ? 'badge-dead' :
                      item.status === 'SENDING' ? 'badge-redirect' : 'badge-unknown'
                    }`}>
                      {item.status}
                    </span>
                  </td>
                  <td>{item.attempts}</td>
                  <td style={{ fontSize: '12px', color: '#94a3b8' }}>
                    {item.sent_at ? new Date(item.sent_at).toLocaleTimeString('en-GB') : '—'}
                  </td>
                  <td style={{ fontSize: '11px', color: item.error_message ? '#fb7185' : '#94a3b8', maxWidth: '200px' }}>
                    {item.error_message || item.message_id || 'Queued'}
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
