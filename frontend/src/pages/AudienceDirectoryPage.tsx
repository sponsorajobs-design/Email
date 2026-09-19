import React, { useState, useEffect, useMemo } from 'react'
import { api } from '../services/api'
import { AudienceCategory, AudienceRecipient } from '../types'

interface AudienceDirectoryPageProps {
  onComposeToCategory: (categoryName: string) => void
}

export const AudienceDirectoryPage: React.FC<AudienceDirectoryPageProps> = ({ onComposeToCategory }) => {
  const [categories, setCategories] = useState<AudienceCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategoryName, setSelectedCategoryName] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const data = await api.getAudienceDirectory()
        setCategories(data)
      } catch (err) {
        console.error('Failed to load directory:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Aggregate all recipients across categories
  const allRecipients = useMemo(() => {
    const list: Array<AudienceRecipient & { categoryName: string; categoryTitle: string; icon: string }> = []
    const seenEmails = new Set<string>()

    categories.forEach(cat => {
      cat.recipients.forEach(r => {
        if (!seenEmails.has(r.email.toLowerCase())) {
          seenEmails.add(r.email.toLowerCase())
          list.push({
            ...r,
            categoryName: cat.category_name,
            categoryTitle: cat.display_title,
            icon: cat.icon
          })
        }
      })
    })
    return list
  }, [categories])

  // Filtered list based on category & search query
  const filteredRecipients = useMemo(() => {
    let result = allRecipients

    if (selectedCategoryName !== 'ALL') {
      result = result.filter(r => r.categoryName === selectedCategoryName)
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(r =>
        r.name.toLowerCase().includes(q) ||
        r.email.toLowerCase().includes(q) ||
        (r.preferred_roles && r.preferred_roles.toLowerCase().includes(q)) ||
        (r.location && r.location.toLowerCase().includes(q))
      )
    }

    return result
  }, [allRecipients, selectedCategoryName, searchQuery])

  const totalSubscribers = allRecipients.length

  return (
    <div className="audience-page-container">
      {/* Header */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            👥 Candidate Audience Directory
          </h1>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '14px' }}>
            Browse your talent pool organized by professional domains. Every category connects directly to your email campaigns.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="badge" style={{ background: '#ecfdf5', color: '#059669', fontSize: '13px', padding: '6px 12px' }}>
            {totalSubscribers} Verified Candidates
          </span>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onComposeToCategory(selectedCategoryName !== 'ALL' ? selectedCategoryName : 'Civil, Construction & Architecture')}
          >
            ✉️ Compose to {selectedCategoryName !== 'ALL' ? 'Selected Group' : 'Candidates'}
          </button>
        </div>
      </div>

      {/* Category Pills Grid */}
      <div className="audience-category-strip">
        <button
          type="button"
          className={`category-filter-chip ${selectedCategoryName === 'ALL' ? 'active' : ''}`}
          onClick={() => setSelectedCategoryName('ALL')}
        >
          <span style={{ fontSize: '16px' }}>🌐</span>
          <span style={{ fontWeight: 600 }}>All Candidates</span>
          <span className="count-chip">{totalSubscribers}</span>
        </button>

        {categories.map(cat => (
          <button
            key={cat.category_name}
            type="button"
            className={`category-filter-chip ${selectedCategoryName === cat.category_name ? 'active' : ''}`}
            onClick={() => setSelectedCategoryName(cat.category_name)}
          >
            <span style={{ fontSize: '16px' }}>{cat.icon}</span>
            <span style={{ fontWeight: 600 }}>{cat.display_title}</span>
            <span className="count-chip">{cat.total_candidates}</span>
          </button>
        ))}
      </div>

      {/* Search and Action Bar */}
      <div className="directory-search-bar" style={{ display: 'flex', gap: '12px', alignItems: 'center', margin: '20px 0 16px 0' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            type="text"
            className="form-control"
            placeholder="Search by candidate name, email, or role title (e.g. Civil Engineer, Project Manager)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '38px', height: '44px', fontSize: '14px' }}
          />
          <span style={{ position: 'absolute', left: '12px', top: '12px', fontSize: '16px', color: 'var(--text-muted)' }}>
            🔍
          </span>
        </div>

        {selectedCategoryName !== 'ALL' && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onComposeToCategory(selectedCategoryName)}
            style={{ height: '44px', whiteSpace: 'nowrap' }}
          >
            ✉️ Send Alert to {selectedCategoryName}
          </button>
        )}
      </div>

      {/* Candidates List Table */}
      <div className="compose-card" style={{ padding: '0', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading candidate directory...
          </div>
        ) : filteredRecipients.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No candidates matched your search query.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--bg-primary)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '12px 16px', width: '220px' }}>Candidate Name</th>
                  <th style={{ padding: '12px 16px' }}>Email Address</th>
                  <th style={{ padding: '12px 16px' }}>Category</th>
                  <th style={{ padding: '12px 16px' }}>Preferred Roles</th>
                  <th style={{ padding: '12px 16px' }}>Location</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecipients.slice(0, 150).map((r, i) => (
                  <tr
                    key={r.id || i}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      transition: 'background 0.15s ease'
                    }}
                    className="table-row-hover"
                  >
                    <td style={{ padding: '10px 16px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {r.name}
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--accent-blue)', fontWeight: 500 }}>
                      {r.email}
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <span className="badge" style={{ background: '#f1f5f9', color: 'var(--text-secondary)' }}>
                        {r.icon} {r.categoryTitle}
                      </span>
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-secondary)' }}>
                      {r.preferred_roles || 'General Professional'}
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>
                      {r.location || 'United Kingdom'}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn-link"
                        onClick={() => onComposeToCategory(r.categoryName)}
                      >
                        Target Group →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ padding: '12px 16px', background: 'var(--bg-primary)', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
          <span>Showing {Math.min(filteredRecipients.length, 150)} of {filteredRecipients.length} candidates</span>
          <span>All records stored locally in SQLite</span>
        </div>
      </div>
    </div>
  )
}
