import React, { useState, useEffect } from 'react'
import { Subscriber, SubscriberSentEmailHistoryItem, CategorySummary, CampaignPreviewItem } from '../types'
import { api } from '../services/api'
import { EmailPreviewModal } from '../components/EmailPreviewModal'

export const SubscribersPage: React.FC = () => {
  const [subscribers, setSubscribers] = useState<Subscriber[]>([])
  const [categories, setCategories] = useState<CategorySummary[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('All')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)

  // Auto-sync state
  const [autoSync, setAutoSync] = useState(false)
  const [syncInterval, setSyncInterval] = useState(15)
  const [updatingSettings, setUpdatingSettings] = useState(false)

  // History modal state
  const [selectedSubscriber, setSelectedSubscriber] = useState<Subscriber | null>(null)
  const [historyItems, setHistoryItems] = useState<SubscriberSentEmailHistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Email Preview modal state
  const [previewItem, setPreviewItem] = useState<CampaignPreviewItem | null>(null)

  // Category "Send in One Go" modal state
  const [showCategorySendModal, setShowCategorySendModal] = useState(false)
  const [dispatchingCategory, setDispatchingCategory] = useState(false)
  const [dispatchResultMsg, setDispatchResultMsg] = useState<string | null>(null)

  const loadData = async (query?: string, cat?: string) => {
    setLoading(true)
    try {
      const activeCat = cat !== undefined ? cat : selectedCategory
      const data = await api.getSubscribers(query, activeCat)
      setSubscribers(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const loadCategories = async () => {
    try {
      const catData = await api.getCategories()
      setCategories(catData)
    } catch (e) {
      console.error('Failed to load categories:', e)
    }
  }

  const loadSettings = async () => {
    try {
      const settings = await api.getSettings()
      if (settings.auto_sync_subscribers !== undefined) {
        setAutoSync(settings.auto_sync_subscribers)
      }
      if (settings.auto_sync_interval_minutes !== undefined) {
        setSyncInterval(settings.auto_sync_interval_minutes)
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }

  useEffect(() => {
    loadData(search, selectedCategory)
    loadCategories()
    loadSettings()
  }, [])

  const handleCategorySelect = (categoryName: string) => {
    setSelectedCategory(categoryName)
    loadData(search, categoryName)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadData(search, selectedCategory)
  }

  const handleManualSync = async () => {
    setSyncing(true)
    setSyncMsg(null)
    try {
      const res = await api.syncSubscribers()
      const result = res.result || {}
      setSyncMsg(`✓ Synced ${result.synced || 0} new candidates, ${result.updated || 0} updated from Supabase.`)
      await loadCategories()
      await loadData(search, selectedCategory)
    } catch (e: any) {
      setSyncMsg(`✗ Sync error: ${e.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleToggleAutoSync = async (enabled: boolean) => {
    setAutoSync(enabled)
    setUpdatingSettings(true)
    try {
      await api.updateSettings({
        auto_sync_subscribers: enabled,
        auto_sync_interval_minutes: syncInterval
      })
      setSyncMsg(enabled 
        ? `✓ Auto-sync enabled! Polling Supabase every ${syncInterval} minutes in background.` 
        : '✓ Auto-sync disabled.'
      )
    } catch (e: any) {
      setAutoSync(!enabled)
      setSyncMsg(`✗ Failed to update auto-sync: ${e.message}`)
    } finally {
      setUpdatingSettings(false)
    }
  }

  const handleChangeInterval = async (minutes: number) => {
    setSyncInterval(minutes)
    if (autoSync) {
      setUpdatingSettings(true)
      try {
        await api.updateSettings({
          auto_sync_subscribers: true,
          auto_sync_interval_minutes: minutes
        })
        setSyncMsg(`✓ Auto-sync interval updated to every ${minutes} minutes.`)
      } catch (e: any) {
        setSyncMsg(`✗ Failed to update interval: ${e.message}`)
      } finally {
        setUpdatingSettings(false)
      }
    }
  }

  const openSentHistory = async (sub: Subscriber) => {
    setSelectedSubscriber(sub)
    setLoadingHistory(true)
    setHistoryItems([])
    try {
      const items = await api.getSubscriberHistory(sub.id)
      setHistoryItems(items)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingHistory(false)
    }
  }

  const openEmailPreview = (s: Subscriber) => {
    if (!s.best_match_job_title) return
    const mockPreview: CampaignPreviewItem = {
      queue_id: s.id,
      subscriber_id: s.id,
      job_id: s.best_match_job_id || 1,
      candidate_name: s.name,
      candidate_email: s.email,
      job_title: s.best_match_job_title || 'Target Role',
      company_name: s.best_match_company || 'SponsorAJobs Partner',
      match_score: s.best_match_score || 85,
      url_status: s.best_match_url_status || 'LIVE',
      status: 'PREVIEW',
      subject: s.email_subject_preview || `Congratulations! Your Profile Has Been Shortlisted for the ${s.best_match_job_title} Role`,
      html_preview: `
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
          <h2 style="color: #0f172a;">Congratulations! Your Profile Has Been Shortlisted</h2>
          <p>Dear <strong>${s.name}</strong>,</p>
          <p>Your profile has been shortlisted by SponsorAJobs for the <strong>${s.best_match_job_title}</strong> role at <strong>${s.best_match_company}</strong> based on your target preferences (Match Score: <strong>${s.best_match_score || 85}%</strong>).</p>
          <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong>Shortlisted Opportunity:</strong><br/>
            Position: ${s.best_match_job_title}<br/>
            Employer: ${s.best_match_company}<br/>
            Location: ${s.location || 'United Kingdom'}<br/>
            Your Stated Experience: ${s.experience_years} years
          </div>
          <p style="text-align: center; margin: 25px 0;">
            <a href="${s.best_match_application_url || 'https://sponsorajobs.com'}" target="_blank" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold;">
              View Job & Apply on SponsorAJobs &rarr;
            </a>
            <br/>
            <span style="font-size: 11px; color: #64748b; margin-top: 6px; display: block;">
              Listing: ${s.best_match_application_url || 'https://sponsorajobs.com'}
            </span>
          </p>
          <p style="font-size: 12px; color: #64748b; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
            <strong>Important Notice:</strong> This shortlist is based on SponsorAJobs' profile-to-opportunity matching and does not represent a final hiring decision by the employer.
          </p>
        </div>
      `
    }
    setPreviewItem(mockPreview)
  }

  // Handle "Send to Category in One Go"
  const handleExecuteCategorySend = async () => {
    if (selectedCategory === 'All') return
    setDispatchingCategory(true)
    setDispatchResultMsg(null)
    try {
      const res = await api.sendCategoryCampaign({
        category: selectedCategory,
        match_threshold: 60,
        batch_size: 50,
        auto_send: true
      })
      setDispatchResultMsg(`✓ Successfully generated and dispatched emails for ${selectedCategory}! (${res.queued || 0} candidates processed)`)
      await loadCategories()
      await loadData(search, selectedCategory)
      setShowCategorySendModal(false)
    } catch (e: any) {
      setDispatchResultMsg(`✗ Dispatch failed: ${e.message}`)
    } finally {
      setDispatchingCategory(false)
    }
  }

  // Find active category summary info
  const activeCategorySummary = categories.find((c) => c.category_name === selectedCategory)
  const readyToSendInActiveCategory = activeCategorySummary ? activeCategorySummary.ready_to_send_count : 0
  const candidatesInActiveCategory = subscribers.filter((s) => s.dispatch_readiness === 'READY_TO_SEND')

  return (
    <div>
      {/* Top Header */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Candidate Profile Categories & Email Dispatch</h2>
          <p className="section-subtitle">
            Subscribers categorized by professional domain with complete email payload details and 1-click batch dispatch.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            className="btn btn-secondary" 
            onClick={() => { loadData(search, selectedCategory); loadCategories(); }} 
            disabled={loading}
          >
            {loading ? 'Refreshing...' : '↻ Refresh List'}
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleManualSync} 
            disabled={syncing}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <span>{syncing ? '⌛' : '⚡'}</span>
            <span>{syncing ? 'Syncing...' : 'Sync New Subscribers'}</span>
          </button>
        </div>
      </div>

      {/* Auto-Sync Configuration Control Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '10px',
        padding: '14px 20px',
        marginBottom: '1.25rem',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '14px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: autoSync ? '#ecfdf5' : '#f1f5f9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px'
          }}>
            {autoSync ? '🔄' : '⏸️'}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a' }}>
                Auto-Update New Subscribers
              </span>
              <span className={`badge ${autoSync ? 'badge-live' : 'badge-neutral'}`} style={{ fontSize: '11px' }}>
                {autoSync ? 'Active Polling' : 'Disabled'}
              </span>
            </div>
            <p style={{ margin: '1px 0 0 0', fontSize: '12px', color: '#64748b' }}>
              Pulls newly added candidates from Supabase in background without interrupting operations.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '13px', color: '#475569', fontWeight: 500 }}>Frequency:</span>
            <select
              value={syncInterval}
              onChange={(e) => handleChangeInterval(Number(e.target.value))}
              disabled={updatingSettings}
              style={{
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '13px',
                background: '#ffffff',
                color: '#0f172a',
                cursor: 'pointer'
              }}
            >
              <option value={5}>Every 5 min</option>
              <option value={15}>Every 15 min</option>
              <option value={30}>Every 30 min</option>
              <option value={60}>Every 1 hour</option>
            </select>
          </div>

          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            padding: '5px 12px',
            background: autoSync ? '#ecfdf5' : '#f8fafc',
            border: `1px solid ${autoSync ? '#a7f3d0' : '#e2e8f0'}`,
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 600,
            color: autoSync ? '#065f46' : '#475569'
          }}>
            <input
              type="checkbox"
              checked={autoSync}
              onChange={(e) => handleToggleAutoSync(e.target.checked)}
              disabled={updatingSettings}
              style={{ width: '15px', height: '15px', cursor: 'pointer' }}
            />
            <span>Enable Auto-Sync</span>
          </label>
        </div>
      </div>

      {/* Notifications / Toast Banner */}
      {(syncMsg || dispatchResultMsg) && (
        <div style={{
          padding: '12px 18px',
          borderRadius: '8px',
          marginBottom: '1.25rem',
          background: (syncMsg?.startsWith('✓') || dispatchResultMsg?.startsWith('✓')) ? '#ecfdf5' : '#fef2f2',
          border: `1px solid ${(syncMsg?.startsWith('✓') || dispatchResultMsg?.startsWith('✓')) ? '#a7f3d0' : '#fecaca'}`,
          color: (syncMsg?.startsWith('✓') || dispatchResultMsg?.startsWith('✓')) ? '#065f46' : '#991b1b',
          fontSize: '13px',
          fontWeight: 600,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{dispatchResultMsg || syncMsg}</span>
          <button
            onClick={() => { setSyncMsg(null); setDispatchResultMsg(null); }}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '14px', color: 'inherit' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Profile Domain Categories Selection Bar */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Profile Domain Categories
          </span>
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            Select a category to filter or send emails in one go
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {/* "All" Tab */}
          <button
            onClick={() => handleCategorySelect('All')}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: selectedCategory === 'All' ? '2px solid var(--primary)' : '1px solid #cbd5e1',
              background: selectedCategory === 'All' ? '#eff6ff' : '#ffffff',
              color: selectedCategory === 'All' ? 'var(--primary)' : '#334155',
              fontWeight: selectedCategory === 'All' ? 700 : 500,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
            }}
          >
            <span>🌐 All Profiles</span>
            <span style={{
              background: selectedCategory === 'All' ? 'var(--primary)' : '#e2e8f0',
              color: selectedCategory === 'All' ? '#ffffff' : '#475569',
              padding: '1px 6px',
              borderRadius: '10px',
              fontSize: '11px',
              fontWeight: 700
            }}>
              {categories.reduce((acc, c) => acc + c.total_candidates, 0)}
            </span>
          </button>

          {/* Individual Categories */}
          {categories.map((c) => {
            const isSelected = selectedCategory === c.category_name
            const hasReady = c.ready_to_send_count > 0
            return (
              <button
                key={c.category_name}
                onClick={() => handleCategorySelect(c.category_name)}
                style={{
                  padding: '8px 14px',
                  borderRadius: '8px',
                  border: isSelected ? '2px solid var(--primary)' : '1px solid #cbd5e1',
                  background: isSelected ? '#eff6ff' : '#ffffff',
                  color: isSelected ? 'var(--primary)' : '#334155',
                  fontWeight: isSelected ? 700 : 500,
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
                }}
              >
                <span>{c.category_name}</span>
                <span style={{
                  background: isSelected ? 'var(--primary)' : '#e2e8f0',
                  color: isSelected ? '#ffffff' : '#475569',
                  padding: '1px 6px',
                  borderRadius: '10px',
                  fontSize: '11px',
                  fontWeight: 700
                }}>
                  {c.total_candidates}
                </span>
                {hasReady && (
                  <span 
                    title={`${c.ready_to_send_count} candidates ready to send`} 
                    style={{
                      background: '#10b981',
                      color: '#ffffff',
                      padding: '1px 5px',
                      borderRadius: '10px',
                      fontSize: '10px',
                      fontWeight: 800
                    }}
                  >
                    ⚡ {c.ready_to_send_count} Ready
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Hero Category Action Card (Send to Category in One Go) */}
      {selectedCategory !== 'All' && activeCategorySummary && (
        <div style={{
          background: 'linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%)',
          border: '1px solid #bae6fd',
          borderRadius: '12px',
          padding: '18px 24px',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a', margin: 0 }}>
                Category: {selectedCategory}
              </h3>
              <span className="badge badge-primary">
                {activeCategorySummary.total_candidates} Candidates
              </span>
              <span className="badge badge-live">
                {activeCategorySummary.live_jobs_count} Live Verified Jobs
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '13px', color: '#475569' }}>
              {readyToSendInActiveCategory > 0 ? (
                <span>
                  🎯 <strong>{readyToSendInActiveCategory} candidates</strong> are qualified and ready to receive personalized shortlisted recommendations.
                </span>
              ) : (
                <span>
                  All candidates in this category have either already been sent their matches, have no live job overlap, or are opted-out.
                </span>
              )}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              className="btn btn-primary"
              onClick={() => setShowCategorySendModal(true)}
              disabled={readyToSendInActiveCategory === 0 || dispatchingCategory}
              style={{
                padding: '10px 20px',
                fontSize: '14px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 12px rgba(37,99,235,0.2)'
              }}
            >
              <span>🚀</span>
              <span>
                {dispatchingCategory ? 'Dispatching...' : `Send to Category (${readyToSendInActiveCategory} Ready) in One Go`}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="action-bar">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', width: '100%', maxWidth: '540px' }}>
          <input
            type="text"
            placeholder="Search candidates by name, email, target role, or skills..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary">
            Search
          </button>
          {search && (
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={() => { setSearch(''); loadData('', selectedCategory); }}
            >
              Clear
            </button>
          )}
        </form>
        <div style={{ color: '#64748b', fontSize: '13px' }}>
          Showing <strong>{subscribers.length}</strong> candidates in <strong>{selectedCategory}</strong>
        </div>
      </div>

      {/* Comprehensive Dispatch Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th style={{ width: '50px' }}>ID</th>
              <th>Candidate & Category</th>
              <th>Profile Highlights</th>
              <th>Shortlisted Job & Employer</th>
              <th>SponsorAJobs Listing</th>
              <th>Match Score</th>
              <th>Subject Line Preview</th>
              <th>Dispatch Readiness</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {subscribers.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', color: '#64748b', padding: '3rem 1rem' }}>
                  {loading ? (
                    <div>Loading category candidates...</div>
                  ) : (
                    <div>
                      <p style={{ fontSize: '15px', fontWeight: 600, marginBottom: '6px' }}>
                        No candidates found for category "{selectedCategory}".
                      </p>
                      <p style={{ fontSize: '13px', color: '#94a3b8' }}>
                        Try selecting another category or click <strong>"Sync New Subscribers"</strong> above.
                      </p>
                    </div>
                  )}
                </td>
              </tr>
            ) : (
              subscribers.map((s) => {
                const isReady = s.dispatch_readiness === 'READY_TO_SEND'
                const isSent = s.dispatch_readiness === 'ALREADY_SENT'
                const isUnsub = s.dispatch_readiness === 'UNSUBSCRIBED'

                return (
                  <tr key={s.id} style={{ background: isReady ? '#f0fdf4' : undefined }}>
                    <td>#{s.id}</td>

                    {/* Candidate Name & Email with direct mailto link */}
                    <td style={{ minWidth: '180px' }}>
                      <strong style={{ color: '#0f172a', fontSize: '14px', display: 'block' }}>
                        {s.name && !/\d/.test(s.name) && !['candidate', 'subscriber', 'applicant', 'user'].includes(s.name.toLowerCase()) ? s.name : 'Candidate'}
                      </strong>
                      <a
                        href={`mailto:${s.email}?subject=Regarding your SponsorAJobs profile`}
                        title={`Send direct email to ${s.email}`}
                        style={{
                          color: 'var(--primary)',
                          textDecoration: 'none',
                          fontWeight: 600,
                          fontSize: '12px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          marginTop: '2px'
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
                        onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
                      >
                        <span>✉️</span>
                        <span>{s.email}</span>
                      </a>
                      <div style={{ marginTop: '4px' }}>
                        <span className="badge" style={{
                          background: '#e0e7ff',
                          color: '#3730a3',
                          fontSize: '10px',
                          fontWeight: 700
                        }}>
                          {s.category}
                        </span>
                      </div>
                    </td>

                    {/* Profile Highlights */}
                    <td style={{ minWidth: '160px', fontSize: '12px', color: '#475569' }}>
                      <div><strong>Exp:</strong> {s.experience_years} yrs • <strong>Loc:</strong> {s.location || 'UK'}</div>
                      <div style={{ color: '#64748b', marginTop: '2px', fontSize: '11px' }} title={s.skills || ''}>
                        <strong>Skills:</strong> {s.skills ? (s.skills.length > 35 ? s.skills.slice(0, 35) + '...' : s.skills) : 'None'}
                      </div>
                    </td>

                    {/* Shortlisted Job & Employer */}
                    <td style={{ minWidth: '180px' }}>
                      {s.best_match_job_title ? (
                        <div>
                          <strong style={{ color: '#0f172a', fontSize: '13px' }}>
                            {s.best_match_job_title}
                          </strong>
                          <div style={{ fontSize: '12px', color: '#475569' }}>
                            🏢 {s.best_match_company}
                          </div>
                        </div>
                      ) : (
                        <span style={{ color: '#94a3b8', fontSize: '12px' }}>No qualifying role</span>
                      )}
                    </td>

                    {/* SponsorAJobs Website Listing & Verification Status */}
                    <td style={{ minWidth: '160px' }}>
                      {s.best_match_application_url ? (
                        <div>
                          <a
                            href={s.best_match_application_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{
                              fontSize: '11px',
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
                          <div style={{ marginTop: '3px' }}>
                            <span className={`badge ${s.best_match_url_status === 'LIVE' ? 'badge-live' : 'badge-neutral'}`} style={{ fontSize: '10px' }}>
                              {s.best_match_url_status === 'LIVE' ? 'VERIFIED ACTIVE' : (s.best_match_url_status || 'PORTAL')}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <span style={{ color: '#94a3b8', fontSize: '12px' }}>—</span>
                      )}
                    </td>

                    {/* Match Score Badge */}
                    <td>
                      {s.best_match_score ? (
                        <span className={`badge ${s.best_match_score >= 85 ? 'badge-live' : 'badge-primary'}`} style={{ fontWeight: 800, fontSize: '12px' }}>
                          {s.best_match_score}%
                        </span>
                      ) : (
                        <span style={{ color: '#94a3b8', fontSize: '12px' }}>—</span>
                      )}
                    </td>

                    {/* Subject Line Preview */}
                    <td style={{ maxWidth: '220px', fontSize: '11px', color: '#334155' }}>
                      {s.email_subject_preview ? (
                        <span title={s.email_subject_preview} style={{ fontStyle: 'italic', display: 'block', lineHeight: 1.4 }}>
                          "{s.email_subject_preview}"
                        </span>
                      ) : (
                        <span style={{ color: '#94a3b8' }}>—</span>
                      )}
                    </td>

                    {/* Dispatch Readiness Status */}
                    <td>
                      {isReady && (
                        <span className="badge badge-live" style={{ fontWeight: 700, fontSize: '11px' }}>
                          ⚡ Ready to Send
                        </span>
                      )}
                      {isSent && (
                        <span className="badge badge-neutral" style={{ fontWeight: 600, fontSize: '11px' }}>
                          ✓ Already Sent
                        </span>
                      )}
                      {isUnsub && (
                        <span className="badge badge-dead" style={{ fontWeight: 600, fontSize: '11px' }}>
                          🚫 Unsubscribed
                        </span>
                      )}
                      {!isReady && !isSent && !isUnsub && (
                        <span className="badge badge-neutral" style={{ color: '#94a3b8', fontSize: '11px' }}>
                          No Match
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        {s.best_match_job_title && (
                          <button
                            className="btn btn-secondary"
                            onClick={() => openEmailPreview(s)}
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            title="Preview rendered email for this candidate"
                          >
                            👁 Preview
                          </button>
                        )}
                        <button
                          className="btn btn-secondary"
                          onClick={() => openSentHistory(s)}
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                          title="View history of sent emails to this candidate"
                        >
                          📊 History ({s.total_emails_sent || 0})
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Modal: Send to Category in One Go Confirmation */}
      {showCategorySendModal && (
        <div className="modal-backdrop" onClick={() => setShowCategorySendModal(false)}>
          <div
            className="modal-card"
            style={{ maxWidth: '780px', width: '95%' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a', margin: 0 }}>
                  🚀 Send Emails to Category: {selectedCategory}
                </h3>
                <p style={{ margin: '3px 0 0 0', fontSize: '13px', color: '#64748b' }}>
                  Review recipients and dispatch personalized shortlisted emails in one go.
                </p>
              </div>
              <button
                className="btn btn-secondary"
                onClick={() => setShowCategorySendModal(false)}
                style={{ padding: '5px 10px', fontSize: '13px' }}
              >
                ✕ Close
              </button>
            </div>

            {/* Overview Stats */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: '12px',
              marginBottom: '1.25rem'
            }}>
              <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>CATEGORY DOMAIN</div>
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>{selectedCategory}</div>
              </div>
              <div style={{ background: '#ecfdf5', padding: '12px', borderRadius: '8px', border: '1px solid #a7f3d0', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#065f46', fontWeight: 600 }}>READY TO DISPATCH</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#059669', marginTop: '2px' }}>{readyToSendInActiveCategory} Candidates</div>
              </div>
              <div style={{ background: '#f0f9ff', padding: '12px', borderRadius: '8px', border: '1px solid #bae6fd', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#0369a1', fontWeight: 600 }}>DELIVERY SAFEGUARDS</div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#0284c7', marginTop: '2px' }}>Dry-Run & Rate Limits Active</div>
              </div>
            </div>

            {/* Candidates to receive email */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
                Recipients & Target Matches:
              </h4>
              <div style={{ maxHeight: '240px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                <table style={{ margin: 0 }}>
                  <thead>
                    <tr>
                      <th>Candidate Name & Email</th>
                      <th>Matched Job</th>
                      <th>Score</th>
                      <th>Subject Line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidatesInActiveCategory.map((c) => (
                      <tr key={c.id}>
                        <td>
                          <strong>{c.name}</strong>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>{c.email}</div>
                        </td>
                        <td>
                          <strong>{c.best_match_job_title}</strong>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>{c.best_match_company}</div>
                        </td>
                        <td>
                          <span className="badge badge-primary">{c.best_match_score}%</span>
                        </td>
                        <td style={{ fontSize: '11px', color: '#334155' }}>
                          "{c.email_subject_preview}"
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowCategorySendModal(false)}
                disabled={dispatchingCategory}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleExecuteCategorySend}
                disabled={dispatchingCategory || readyToSendInActiveCategory === 0}
                style={{ padding: '8px 20px', fontWeight: 700 }}
              >
                {dispatchingCategory ? 'Sending Campaign...' : `Confirm & Dispatch to ${selectedCategory} in One Go`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rendered Email Preview Modal */}
      {previewItem && (
        <EmailPreviewModal
          item={previewItem}
          onClose={() => setPreviewItem(null)}
        />
      )}

      {/* Sent Email History Audit Trail Modal */}
      {selectedSubscriber && (
        <div className="modal-backdrop" onClick={() => setSelectedSubscriber(null)}>
          <div 
            className="modal-card" 
            style={{ maxWidth: '850px', width: '95%' }} 
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a', margin: 0 }}>
                    Sent Email Audit Trail: {selectedSubscriber.name}
                  </h3>
                  <span className={`badge ${selectedSubscriber.is_unsubscribed ? 'badge-dead' : 'badge-live'}`}>
                    {selectedSubscriber.is_unsubscribed ? 'Unsubscribed' : 'Active Subscriber'}
                  </span>
                </div>
                <div style={{ marginTop: '4px', fontSize: '13px', color: '#64748b', display: 'flex', gap: '12px' }}>
                  <span>
                    Email:{' '}
                    <a 
                      href={`mailto:${selectedSubscriber.email}`} 
                      style={{ color: 'var(--primary)', fontWeight: 600, textDecoration: 'underline' }}
                    >
                      {selectedSubscriber.email}
                    </a>
                  </span>
                  <span>•</span>
                  <span>Category: <strong>{selectedSubscriber.category}</strong></span>
                </div>
              </div>
              <button 
                className="btn btn-secondary" 
                onClick={() => setSelectedSubscriber(null)}
                style={{ padding: '6px 12px', fontSize: '13px' }}
              >
                ✕ Close
              </button>
            </div>

            {/* Modal Content */}
            {loadingHistory ? (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#64748b' }}>
                Loading email dispatch records...
              </div>
            ) : historyItems.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '3rem 2rem',
                background: '#f8fafc',
                border: '1px dashed #cbd5e1',
                borderRadius: '8px'
              }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>📭</div>
                <h4 style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
                  No Emails Sent Yet
                </h4>
                <p style={{ fontSize: '13px', color: '#64748b', maxWidth: '440px', margin: '0 auto' }}>
                  Zero campaigns have been dispatched to <strong>{selectedSubscriber.email}</strong>. Once a campaign match is approved and sent, the full delivery record with timestamp and job details will be catalogued here.
                </p>
              </div>
            ) : (
              <div>
                <div style={{ 
                  marginBottom: '1rem', 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  background: '#f8fafc',
                  padding: '10px 16px',
                  borderRadius: '6px',
                  border: '1px solid #e2e8f0'
                }}>
                  <span style={{ fontSize: '13px', color: '#334155' }}>
                    Total Dispatches: <strong>{historyItems.length}</strong>
                  </span>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>
                    Duplicate Protection: Candidates will not receive redundant notifications for the same role.
                  </span>
                </div>

                <div className="table-container" style={{ maxHeight: '420px', overflowY: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Date & Time Sent</th>
                        <th>Recommended Job</th>
                        <th>Company</th>
                        <th>Match Score</th>
                        <th>Campaign</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyItems.map((item) => (
                        <tr key={item.id}>
                          <td style={{ whiteSpace: 'nowrap', fontSize: '12px', fontWeight: 500, color: '#0f172a' }}>
                            {item.sent_at ? (
                              new Date(item.sent_at).toLocaleString('en-GB', {
                                day: '2-digit',
                                month: 'short',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })
                            ) : (
                              'Recently'
                            )}
                          </td>
                          <td>
                            <strong style={{ color: '#0f172a', fontSize: '13px' }}>{item.job_title}</strong>
                            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                              Subject: <em>"{item.subject}"</em>
                            </div>
                          </td>
                          <td style={{ fontSize: '13px', color: '#334155' }}>{item.company_name}</td>
                          <td>
                            <span className="badge badge-primary" style={{ fontWeight: 700 }}>
                              {item.match_score}%
                            </span>
                          </td>
                          <td style={{ fontSize: '12px', color: '#64748b' }}>
                            {item.campaign_name || `Campaign #${item.campaign_id}`}
                          </td>
                          <td>
                            <span className="badge badge-live">
                              {item.status || 'SENT'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Modal Footer */}
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button 
                className="btn btn-primary" 
                onClick={() => setSelectedSubscriber(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
