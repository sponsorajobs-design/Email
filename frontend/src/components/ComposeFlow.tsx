import React, { useState, useEffect, useMemo } from 'react'
import { api } from '../services/api'
import { AudienceCategory, AudienceRecipient, CustomPreviewResponse, DashboardStats } from '../types'

interface ComposeFlowProps {
  stats: DashboardStats | null
  onCampaignCreated?: () => void
  onOpenSettings?: () => void
  initialCategory?: string | null
}

export const ComposeFlow: React.FC<ComposeFlowProps> = ({
  stats,
  onCampaignCreated,
  onOpenSettings,
  initialCategory
}) => {
  // Audience categories
  const [categories, setCategories] = useState<AudienceCategory[]>([])
  const [loadingAudience, setLoadingAudience] = useState(true)
  const [selectedCategoryNames, setSelectedCategoryNames] = useState<string[]>([])
  const [excludedSubscriberIds, setExcludedSubscriberIds] = useState<Set<number>>(new Set())

  // Modal to inspect candidate emails
  const [inspectCategory, setInspectCategory] = useState<AudienceCategory | null>(null)
  const [inspectSearch, setInspectSearch] = useState('')

  // Job Details
  const [jobTitle, setJobTitle] = useState('')
  const [jobLink, setJobLink] = useState('')
  const [location, setLocation] = useState('United Kingdom')
  const [employmentType, setEmploymentType] = useState('Full-time')
  const [customMessage, setCustomMessage] = useState('')
  const [showOptionalFields, setShowOptionalFields] = useState(false)

  // Mobile View Switcher ('compose' vs 'preview')
  const [mobileTab, setMobileTab] = useState<'compose' | 'preview'>('compose')

  // Live Email Preview
  const [previewData, setPreviewData] = useState<CustomPreviewResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Sending State
  const [testSending, setTestSending] = useState(false)
  const [showTestModal, setShowTestModal] = useState(false)
  const [testRecipientInput, setTestRecipientInput] = useState<string>(() => {
    return localStorage.getItem('preferred_test_email') || stats?.test_email_address || 'hr@sponsorajobs.com'
  })
  const [campaignSending, setCampaignSending] = useState(false)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; title: string; desc: string } | null>(null)

  useEffect(() => {
    if (stats?.test_email_address && !localStorage.getItem('preferred_test_email')) {
      setTestRecipientInput(stats.test_email_address)
    }
  }, [stats])

  // Load audience categories
  useEffect(() => {
    const loadAudience = async () => {
      setLoadingAudience(true)
      try {
        const data = await api.getAudienceDirectory()
        setCategories(data)
        if (initialCategory) {
          setSelectedCategoryNames([initialCategory])
        } else if (data.length > 0 && selectedCategoryNames.length === 0) {
          const civilCat = data.find(c => c.category_name.toLowerCase().includes('civil'))
          if (civilCat) {
            setSelectedCategoryNames([civilCat.category_name])
          } else {
            setSelectedCategoryNames([data[0].category_name])
          }
        }
      } catch (e) {
        console.error('Failed to load audience:', e)
      } finally {
        setLoadingAudience(false)
      }
    }
    loadAudience()
  }, [initialCategory])

  // Calculate selected recipients count
  const { totalSelectedCount, selectedRecipientsList } = useMemo(() => {
    const list: AudienceRecipient[] = []
    const seenEmails = new Set<string>()

    categories.forEach(cat => {
      if (selectedCategoryNames.includes(cat.category_name)) {
        cat.recipients.forEach(r => {
          if (!excludedSubscriberIds.has(r.id) && !seenEmails.has(r.email.toLowerCase())) {
            seenEmails.add(r.email.toLowerCase())
            list.push(r)
          }
        })
      }
    })

    return { totalSelectedCount: list.length, selectedRecipientsList: list }
  }, [categories, selectedCategoryNames, excludedSubscriberIds])

  // Real-time Preview debounce
  useEffect(() => {
    const timer = setTimeout(async () => {
      setPreviewLoading(true)
      try {
        const preview = await api.previewCustomEmail({
          job_title: jobTitle.trim() || 'Senior Civil Engineer',
          job_link: jobLink.trim() || 'https://sponsorajobs.com/jobs/sample',
          location: location.trim() || 'United Kingdom',
          employment_type: employmentType.trim() || 'Full-time',
          custom_message: customMessage.trim() || undefined
        })
        setPreviewData(preview)
      } catch (err) {
        console.error('Failed to fetch preview:', err)
      } finally {
        setPreviewLoading(false)
      }
    }, 200)

    return () => clearTimeout(timer)
  }, [jobTitle, jobLink, location, employmentType, customMessage])

  // Toggle Category selection
  const toggleCategory = (catName: string) => {
    if (selectedCategoryNames.includes(catName)) {
      setSelectedCategoryNames(selectedCategoryNames.filter(c => c !== catName))
    } else {
      setSelectedCategoryNames([...selectedCategoryNames, catName])
    }
  }

  const selectAllCategories = () => {
    setSelectedCategoryNames(categories.map(c => c.category_name))
  }

  const clearCategories = () => {
    setSelectedCategoryNames([])
  }

  // Open Test Modal
  const handleOpenTestModal = () => {
    if (!jobTitle.trim()) {
      setToastMessage({
        type: 'error',
        title: 'Job Title Required',
        desc: 'Please enter a job title before sending a test.'
      })
      return
    }
    if (!jobLink.trim()) {
      setToastMessage({
        type: 'error',
        title: 'Application Link Required',
        desc: 'Please provide the application link to embed.'
      })
      return
    }
    setShowTestModal(true)
  }

  // Execute Send Test Email
  const handleExecuteSendTest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const targetEmail = (testRecipientInput || 'hr@sponsorajobs.com').trim()
    localStorage.setItem('preferred_test_email', targetEmail)

    setTestSending(true)
    try {
      const res = await api.directSendCampaign({
        job_title: jobTitle.trim(),
        job_link: jobLink.trim(),
        location: location.trim(),
        employment_type: employmentType.trim(),
        custom_message: customMessage.trim() || undefined,
        is_test_send: true,
        test_recipient: targetEmail
      })
      setShowTestModal(false)
      setToastMessage({
        type: 'success',
        title: 'Test Email Dispatched!',
        desc: `Preview successfully delivered to ${res.recipient || targetEmail}. Check your inbox!`
      })
    } catch (err: any) {
      setToastMessage({
        type: 'error',
        title: 'Test Send Failed',
        desc: err.message || 'Could not dispatch test email. Please check that the mailbox exists.'
      })
    } finally {
      setTestSending(false)
    }
  }

  // Launch Campaign
  const handleLaunchCampaign = async () => {
    if (!jobTitle.trim()) {
      setToastMessage({
        type: 'error',
        title: 'Job Title Required',
        desc: 'Please enter a job title.'
      })
      return
    }
    if (!jobLink.trim()) {
      setToastMessage({
        type: 'error',
        title: 'Application Link Required',
        desc: 'Please enter the application link to embed.'
      })
      return
    }
    if (totalSelectedCount === 0) {
      setToastMessage({
        type: 'error',
        title: 'No Recipients Selected',
        desc: 'Please select at least one role category above.'
      })
      return
    }

    setShowConfirmModal(false)
    setCampaignSending(true)

    try {
      const res = await api.directSendCampaign({
        job_title: jobTitle.trim(),
        job_link: jobLink.trim(),
        location: location.trim(),
        employment_type: employmentType.trim(),
        selected_categories: selectedCategoryNames,
        selected_subscriber_ids: selectedRecipientsList.map(r => r.id),
        custom_message: customMessage.trim() || undefined,
        is_test_send: false
      })

      setToastMessage({
        type: 'success',
        title: 'Campaign Dispatched Successfully!',
        desc: `Delivered to ${res.sent_count || totalSelectedCount} candidates (${res.failed_count || 0} failed).`
      })

      if (onCampaignCreated) {
        onCampaignCreated()
      }
    } catch (err: any) {
      setToastMessage({
        type: 'error',
        title: 'Campaign Dispatch Failed',
        desc: err.message || 'Could not send campaign.'
      })
    } finally {
      setCampaignSending(false)
    }
  }

  return (
    <div className="tech-compose-wrapper">
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`tech-toast ${toastMessage.type}`} onClick={() => setToastMessage(null)}>
          <div style={{ fontSize: '18px' }}>{toastMessage.type === 'success' ? '✓' : '⚠'}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: '13px' }}>{toastMessage.title}</div>
            <div style={{ fontSize: '12px', opacity: 0.9 }}>{toastMessage.desc}</div>
          </div>
          <button className="btn-close" style={{ color: 'inherit', fontSize: '18px' }} onClick={() => setToastMessage(null)}>&times;</button>
        </div>
      )}

      {/* Top Mobile Tab Switcher (Visible on small screens) */}
      <div className="mobile-view-tabs">
        <button
          type="button"
          className={`mobile-tab-btn ${mobileTab === 'compose' ? 'active' : ''}`}
          onClick={() => setMobileTab('compose')}
        >
          ⚡ 1. Compose & Roles
        </button>
        <button
          type="button"
          className={`mobile-tab-btn ${mobileTab === 'preview' ? 'active' : ''}`}
          onClick={() => setMobileTab('preview')}
        >
          📱 2. Live Email ({totalSelectedCount})
        </button>
      </div>

      {/* Main Grid: Left is Form, Right is Preview */}
      <div className="tech-grid">
        {/* LEFT COLUMN: COMPOSE CONTROLS */}
        <div className={`tech-form-pane ${mobileTab === 'preview' ? 'hide-on-mobile' : ''}`}>
          
          {/* STEP 1: AUDIENCE SELECTION */}
          <div className="tech-card">
            <div className="tech-card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="step-tag">01</span>
                <div>
                  <h2 className="tech-card-title">Target Candidate Roles</h2>
                  <p className="tech-card-desc">Select who should receive this job alert.</p>
                </div>
              </div>

              <div className="pill-actions">
                <button type="button" className="tech-link-btn" onClick={selectAllCategories}>All</button>
                <span style={{ color: '#94a3b8' }}>/</span>
                <button type="button" className="tech-link-btn" onClick={clearCategories}>Clear</button>
              </div>
            </div>

            {loadingAudience ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                Loading candidate pool...
              </div>
            ) : (
              <div className="tech-pills-wrap">
                {categories.map(cat => {
                  const isSelected = selectedCategoryNames.includes(cat.category_name)
                  return (
                    <button
                      key={cat.category_name}
                      type="button"
                      className={`tech-audience-pill ${isSelected ? 'selected' : ''}`}
                      onClick={() => toggleCategory(cat.category_name)}
                    >
                      <span className="pill-icon">{cat.icon}</span>
                      <span className="pill-name">{cat.display_title.replace(' & Construction', '').replace(' Specialists', '').replace(' Developers', '')}</span>
                      <span className="pill-count">{cat.total_candidates}</span>
                      {isSelected && <span className="pill-check">✓</span>}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Target Status Bar */}
            <div className="tech-audience-bar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="pulse-dot"></span>
                <span style={{ fontSize: '13px', fontWeight: 600 }}>
                  <strong>{totalSelectedCount}</strong> Candidates Selected
                </span>
              </div>
              {totalSelectedCount > 0 && (
                <button
                  type="button"
                  className="tech-link-btn"
                  style={{ fontSize: '12px' }}
                  onClick={() => {
                    setInspectCategory({
                      category_name: 'Selected Recipients',
                      display_title: `All Selected Candidates (${totalSelectedCount})`,
                      icon: '🎯',
                      total_candidates: totalSelectedCount,
                      recipients: selectedRecipientsList
                    })
                    setInspectSearch('')
                  }}
                >
                  Inspect Email List →
                </button>
              )}
            </div>
          </div>

          {/* STEP 2: JOB DETAILS & LINK EMBED */}
          <div className="tech-card">
            <div className="tech-card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="step-tag">02</span>
                <div>
                  <h2 className="tech-card-title">Job Details & Link</h2>
                  <p className="tech-card-desc">The link will be embedded directly into the apply button.</p>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '10px' }}>
              {/* Job Title */}
              <div>
                <label className="tech-label">Job Title *</label>
                <input
                  type="text"
                  className="tech-input"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="e.g. Civil Engineer, Project Manager, Site Supervisor..."
                  required
                />
              </div>

              {/* Job Link (Embedded) */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label className="tech-label" style={{ margin: 0 }}>Application URL (Embedded in Button) *</label>
                  <span className="tech-pill-badge">🔗 Embedded in button</span>
                </div>
                <input
                  type="url"
                  className="tech-input tech-link-input"
                  value={jobLink}
                  onChange={(e) => setJobLink(e.target.value)}
                  placeholder="https://sponsorajobs.com/jobs/civil-engineer-london"
                  required
                />
              </div>

              {/* Optional Details Accordion */}
              <div>
                <button
                  type="button"
                  className="tech-accordion-btn"
                  onClick={() => setShowOptionalFields(!showOptionalFields)}
                >
                  <span>{showOptionalFields ? '▾' : '▸'} Location & Custom Note (Optional)</span>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>{showOptionalFields ? 'Hide' : 'Add'}</span>
                </button>

                {showOptionalFields && (
                  <div className="tech-accordion-body">
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                      <div>
                        <label className="tech-label">Location</label>
                        <input
                          type="text"
                          className="tech-input"
                          value={location}
                          onChange={(e) => setLocation(e.target.value)}
                          placeholder="e.g. London, United Kingdom"
                        />
                      </div>
                      <div>
                        <label className="tech-label">Job Type</label>
                        <input
                          type="text"
                          className="tech-input"
                          value={employmentType}
                          onChange={(e) => setEmploymentType(e.target.value)}
                          placeholder="e.g. Full-time, Contract"
                        />
                      </div>
                    </div>

                    <div style={{ marginTop: '10px' }}>
                      <label className="tech-label">Custom Note to Candidate</label>
                      <textarea
                        className="tech-input"
                        rows={2}
                        value={customMessage}
                        onChange={(e) => setCustomMessage(e.target.value)}
                        placeholder="Add any specific instruction or shortlist note..."
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* DESKTOP ACTION BAR */}
          <div className="tech-card desktop-action-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#64748b' }}>Target Audience</div>
                <div style={{ fontSize: '15px', fontWeight: 800, color: '#0f172a' }}>
                  {totalSelectedCount > 0 ? `${totalSelectedCount} Candidate Emails` : 'No Roles Selected'}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  className="tech-btn-secondary"
                  onClick={handleOpenTestModal}
                  disabled={testSending || campaignSending}
                >
                  {testSending ? 'Sending...' : '✉️ Send Test to Me'}
                </button>

                <button
                  type="button"
                  className="tech-btn-primary"
                  onClick={() => setShowConfirmModal(true)}
                  disabled={totalSelectedCount === 0 || !jobTitle.trim() || !jobLink.trim() || campaignSending}
                >
                  {campaignSending ? 'Dispatching...' : `🚀 Send to ${totalSelectedCount} Candidates`}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: REALISTIC EMAIL PREVIEW */}
        <div className={`tech-preview-pane ${mobileTab === 'compose' ? 'hide-on-mobile' : ''}`}>
          <div className="tech-preview-card">
            <div className="preview-top-bar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="dot dot-red"></span>
                <span className="dot dot-yellow"></span>
                <span className="dot dot-green"></span>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#64748b', marginLeft: '6px' }}>
                  SponsorAJobs Email Client Preview
                </span>
              </div>
              <span className="tech-pill-badge" style={{ background: '#ecfdf5', color: '#059669' }}>
                Authentic 1-on-1 Format
              </span>
            </div>

            {/* Email Header Info */}
            <div className="email-header-meta">
              <div className="recruiter-profile-row">
                <div className="recruiter-avatar">
                  SJ
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>
                    Sarah Jenkins <span style={{ fontWeight: 400, color: '#64748b', fontSize: '12px' }}>&lt;jobs@sponsorajobs.com&gt;</span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    Talent Acquisition | SponsorAJobs
                  </div>
                </div>
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>Just now</span>
              </div>

              <div className="subject-line-box">
                <span style={{ fontWeight: 700, color: '#475569', fontSize: '12px' }}>Subject:</span>{' '}
                <span style={{ fontWeight: 600, color: '#0f172a', fontSize: '13px' }}>
                  {previewData?.subject || `Your profile has been shortlisted for the ${jobTitle || '[Job Title]'} position`}
                </span>
              </div>
            </div>

            {/* Rendered Email Body */}
            <div className="email-body-scroll">
              {previewLoading ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                  Updating email preview...
                </div>
              ) : previewData?.html_body ? (
                <iframe
                  title="Live Email"
                  srcDoc={previewData.html_body}
                  className="real-email-iframe"
                  sandbox="allow-same-origin allow-popups"
                />
              ) : (
                <div style={{ padding: '30px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                  Enter a job title and link to generate preview.
                </div>
              )}
            </div>

            <div className="preview-footer-note">
              ✓ Clean, authentic recruiter email with embedded link button & zero marketing spam.
            </div>
          </div>
        </div>
      </div>

      {/* STICKY BOTTOM BAR FOR MOBILE */}
      <div className="mobile-sticky-action-bar">
        <div style={{ display: 'flex', gap: '8px', width: '100%' }}>
          <button
            type="button"
            className="tech-btn-secondary"
            style={{ flex: 1, padding: '12px', fontSize: '13px' }}
            onClick={handleOpenTestModal}
            disabled={testSending || campaignSending}
          >
            {testSending ? 'Sending...' : '✉️ Test'}
          </button>
          <button
            type="button"
            className="tech-btn-primary"
            style={{ flex: 2, padding: '12px', fontSize: '13px' }}
            onClick={() => setShowConfirmModal(true)}
            disabled={totalSelectedCount === 0 || !jobTitle.trim() || !jobLink.trim() || campaignSending}
          >
            {campaignSending ? 'Sending...' : `🚀 Send to ${totalSelectedCount}`}
          </button>
        </div>
      </div>

      {/* Test Email Destination Modal */}
      {showTestModal && (
        <div className="modal-overlay" onClick={() => setShowTestModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '22px' }}>✉️</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 800 }}>Send Test Email</h3>
                  <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>
                    Deliver a live recruiter preview to your inbox.
                  </p>
                </div>
              </div>
              <button className="btn-close" onClick={() => setShowTestModal(false)}>&times;</button>
            </div>

            <form onSubmit={handleExecuteSendTest} style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '16px' }}>
              <div>
                <label className="tech-label" style={{ marginBottom: '6px' }}>Send Test To (Email Address) *</label>
                <input
                  type="email"
                  required
                  className="tech-input"
                  placeholder="e.g. hr@sponsorajobs.com or your personal email"
                  value={testRecipientInput}
                  onChange={(e) => setTestRecipientInput(e.target.value)}
                  autoFocus
                />
                <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                  Your SMTP server (mail.sponsorajobs.com) requires an active mailbox.
                </div>
              </div>

              <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}>
                <div style={{ fontWeight: 600, color: '#334155' }}>Preview Details:</div>
                <div style={{ color: '#64748b', marginTop: '2px' }}>Role: <span style={{ fontWeight: 600, color: '#0f172a' }}>{jobTitle || 'Role Title'}</span></div>
                <div style={{ color: '#64748b' }}>Sender: <span style={{ fontWeight: 600, color: '#0f172a' }}>Sarah Jenkins &lt;jobs@sponsorajobs.com&gt;</span></div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
                <button
                  type="button"
                  className="tech-btn-secondary"
                  onClick={() => setShowTestModal(false)}
                  disabled={testSending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="tech-btn-primary"
                  disabled={testSending || !testRecipientInput.trim()}
                >
                  {testSending ? 'Sending Test...' : '🚀 Send Test Now'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="modal-overlay" onClick={() => setShowConfirmModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '22px' }}>🚀</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 800 }}>Confirm Dispatch</h3>
                  <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>
                    Send authentic shortlist emails to candidates.
                  </p>
                </div>
              </div>
              <button className="btn-close" onClick={() => setShowConfirmModal(false)}>&times;</button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '14px' }}>
              <div className="confirm-summary-item">
                <span className="confirm-label">Position:</span>
                <span className="confirm-val" style={{ fontWeight: 700 }}>{jobTitle}</span>
              </div>
              <div className="confirm-summary-item">
                <span className="confirm-label">Embedded Link:</span>
                <span className="confirm-val" style={{ color: '#2563eb', wordBreak: 'break-all', fontSize: '12px' }}>
                  {jobLink}
                </span>
              </div>
              <div className="confirm-summary-item">
                <span className="confirm-label">Target Roles:</span>
                <span className="confirm-val">{selectedCategoryNames.join(', ')}</span>
              </div>
              <div className="confirm-summary-item">
                <span className="confirm-label">Total Recipients:</span>
                <span className="confirm-val" style={{ fontWeight: 700, color: '#059669' }}>
                  {totalSelectedCount} Candidates
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '14px' }}>
                <button type="button" className="tech-btn-secondary" onClick={() => setShowConfirmModal(false)}>
                  Cancel
                </button>
                <button type="button" className="tech-btn-primary" onClick={handleLaunchCampaign}>
                  Confirm & Send Now
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Inspect Candidates Modal */}
      {inspectCategory && (
        <div className="modal-overlay" onClick={() => setInspectCategory(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 700 }}>
                  {inspectCategory.display_title}
                </h3>
                <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>
                  {inspectCategory.recipients.length} candidate emails linked to this category.
                </p>
              </div>
              <button className="btn-close" onClick={() => setInspectCategory(null)}>&times;</button>
            </div>

            <div style={{ marginTop: '10px' }}>
              <input
                type="text"
                className="tech-input"
                placeholder="Search candidates by name, email, or role..."
                value={inspectSearch}
                onChange={(e) => setInspectSearch(e.target.value)}
              />
            </div>

            <div style={{ flex: 1, overflowY: 'auto', marginTop: '10px', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px', width: '36px' }}>Send</th>
                    <th style={{ padding: '8px 12px' }}>Name</th>
                    <th style={{ padding: '8px 12px' }}>Email</th>
                    <th style={{ padding: '8px 12px' }}>Preferred Roles</th>
                  </tr>
                </thead>
                <tbody>
                  {inspectCategory.recipients
                    .filter(r => {
                      if (!inspectSearch.trim()) return true
                      const q = inspectSearch.toLowerCase()
                      return (
                        r.name.toLowerCase().includes(q) ||
                        r.email.toLowerCase().includes(q) ||
                        (r.preferred_roles && r.preferred_roles.toLowerCase().includes(q))
                      )
                    })
                    .map(r => {
                      const isExcluded = excludedSubscriberIds.has(r.id)
                      return (
                        <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9', background: isExcluded ? '#fef2f2' : 'transparent' }}>
                          <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={!isExcluded}
                              onChange={() => {
                                const next = new Set(excludedSubscriberIds)
                                if (isExcluded) next.delete(r.id)
                                else next.add(r.id)
                                setExcludedSubscriberIds(next)
                              }}
                              style={{ cursor: 'pointer' }}
                            />
                          </td>
                          <td style={{ padding: '8px 12px', fontWeight: 600 }}>{r.name}</td>
                          <td style={{ padding: '8px 12px', color: '#2563eb' }}>{r.email}</td>
                          <td style={{ padding: '8px 12px', color: '#64748b' }}>{r.preferred_roles || 'Professional'}</td>
                        </tr>
                      )
                    })}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
              <button type="button" className="tech-btn-primary" onClick={() => setInspectCategory(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
