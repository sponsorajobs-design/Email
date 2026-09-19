import React, { useState } from 'react'

interface CampaignModalProps {
  isOpen: boolean
  onClose: () => void
  onGenerate: (payload: { name: string; match_threshold: number; batch_size: number; notes?: string }) => void
  loading: boolean
}

export const CampaignModal: React.FC<CampaignModalProps> = ({ isOpen, onClose, onGenerate, loading }) => {
  const [name, setName] = useState(`Campaign — ${new Date().toLocaleDateString('en-GB')}`)
  const [threshold, setThreshold] = useState(1) // Role alert matching evaluates exact/synonym relevance
  const [batchSize, setBatchSize] = useState(350)
  const [category, setCategory] = useState('ALL')
  const [notes, setNotes] = useState('')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return
    onGenerate({
      name,
      match_threshold: threshold,
      batch_size: batchSize,
      category: category === 'ALL' ? undefined : category,
      notes
    } as any)
  }

  return (
    <div className="modal-overlay" onClick={loading ? undefined : onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '540px' }}>
        <div className="modal-header">
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '800', color: '#f8fafc' }}>
              Create & Generate Campaign
            </h3>
            <p style={{ fontSize: '12px', color: '#94a3b8' }}>
              Automatically evaluates active subscribers, pairs maximum 1 job, and generates reviewable compositions.
            </p>
          </div>
          <button className="modal-close" onClick={onClose} disabled={loading}>✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Campaign Name
            </label>
            <input
              type="text"
              style={{ width: '100%' }}
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Target Domain / Category
            </label>
            <select
              style={{ width: '100%' }}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={loading}
            >
              <option value="ALL">🌐 All Domains & Categories</option>
              <option value="construction">🏗️ Construction & Civil Engineering</option>
              <option value="engineering">⚙️ Engineering & Technical</option>
              <option value="information-technology">💻 Information Technology & Software</option>
              <option value="finance">💼 Finance & Banking</option>
              <option value="logistics">📦 Logistics & Supply Chain</option>
              <option value="hospitality">🏨 Hospitality & Services</option>
              <option value="healthcare">🩺 Healthcare & Medical</option>
              <option value="education">🎓 Education & Training</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Batch Limit
              </label>
              <select
                style={{ width: '100%' }}
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                disabled={loading}
              >
                <option value={10}>10 Subscribers (Test)</option>
                <option value={25}>25 Subscribers</option>
                <option value={50}>50 Subscribers</option>
                <option value={100}>100 Subscribers</option>
                <option value={358}>All Active Subscribers (~358)</option>
                <option value={500}>500 Max Cap</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Safety Gate
              </label>
              <div style={{ padding: '8px 10px', background: '#1e293b', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontSize: '12px', color: '#38bdf8', height: '38px', display: 'flex', alignItems: 'center' }}>
                ✓ Generated in READY (No Auto-Send)
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Campaign Notes (Optional)
            </label>
            <textarea
              style={{ width: '100%', height: '70px' }}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={loading}
              placeholder="e.g. Weekly role alert distribution for all active candidates"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Evaluating & Generating...' : '⚡ Generate Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
