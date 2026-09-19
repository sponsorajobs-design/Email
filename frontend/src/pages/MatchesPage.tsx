import React, { useState, useEffect } from 'react'
import { Match } from '../types'
import { api } from '../services/api'

export const MatchesPage: React.FC = () => {
  const [matches, setMatches] = useState<Match[]>([])
  const [minScore, setMinScore] = useState<number>(70)
  const [calculating, setCalculating] = useState(false)
  const [loading, setLoading] = useState(false)

  const loadMatches = async (score: number) => {
    setLoading(true)
    try {
      const data = await api.getMatches(score)
      setMatches(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMatches(minScore)
  }, [minScore])

  const handleRunMatching = async () => {
    setCalculating(true)
    try {
      await api.runMatching(minScore)
      await loadMatches(minScore)
    } catch (e) {
      console.error(e)
    } finally {
      setCalculating(false)
    }
  }

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">Candidate-Job Matching Engine</h2>
          <p className="section-subtitle">
            Deterministic 100-point scoring algorithm comparing roles, skills, experience, and location.
          </p>
        </div>
        <button className="btn btn-primary" onClick={handleRunMatching} disabled={calculating}>
          {calculating ? 'Evaluating Candidates...' : '⚡ Recalculate All Matches'}
        </button>
      </div>

      <div className="action-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', color: '#94a3b8' }}>Minimum Score Threshold:</span>
          <input
            type="range"
            min="50"
            max="95"
            step="5"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            style={{ width: '180px' }}
          />
          <strong style={{ color: '#38bdf8', fontSize: '15px' }}>{minScore}+ points</strong>
        </div>
        <div style={{ fontSize: '13px', color: '#64748b' }}>
          {matches.length} qualifying match pairings
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Score</th>
              <th>Candidate</th>
              <th>Target Job</th>
              <th>Score Breakdown</th>
              <th>Why Shortlisted (Human-Readable Reasons)</th>
            </tr>
          </thead>
          <tbody>
            {matches.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                  {loading ? 'Loading matches...' : 'No matches found above this threshold. Click "Recalculate All Matches".'}
                </td>
              </tr>
            ) : (
              matches.map((m) => (
                <tr key={m.id}>
                  <td>
                    <div style={{
                      background: m.match_score >= 85 ? '#ecfdf5' : '#eff6ff',
                      color: m.match_score >= 85 ? '#059669' : '#2563eb',
                      border: `1px solid ${m.match_score >= 85 ? '#a7f3d0' : '#bfdbfe'}`,
                      padding: '6px 12px',
                      borderRadius: '8px',
                      fontWeight: 800,
                      fontSize: '15px',
                      textAlign: 'center',
                      display: 'inline-block'
                    }}>
                      {m.match_score}
                    </div>
                  </td>
                  <td>
                    <strong>{m.candidate_name}</strong>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{m.candidate_email}</div>
                  </td>
                  <td>
                    <strong>{m.job_title}</strong>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{m.company_name}</div>
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)', minWidth: '160px' }}>
                    <div>Role: <strong style={{ color: 'var(--text-primary)' }}>{m.role_score}/35</strong></div>
                    <div>Skills: <strong style={{ color: 'var(--text-primary)' }}>{m.skills_score}/30</strong></div>
                    <div>Exp: <strong style={{ color: 'var(--text-primary)' }}>{m.experience_score}/20</strong></div>
                    <div>Loc: <strong style={{ color: 'var(--text-primary)' }}>{m.location_score}/10</strong></div>
                  </td>
                  <td style={{ fontSize: '12px', maxWidth: '380px' }}>
                    <ul style={{ paddingLeft: '14px', margin: 0, color: 'var(--text-secondary)' }}>
                      {(m.match_reasons || '').split('\n').filter(Boolean).map((r, idx) => (
                        <li key={idx} style={{ marginBottom: '2px' }}>{r}</li>
                      ))}
                    </ul>
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
