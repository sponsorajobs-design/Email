import React from 'react'

interface NavbarProps {
  activeTab: string
  setActiveTab: (tab: string) => void
  dryRun: boolean
  testMode: boolean
  onOpenSettings: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  dryRun,
  testMode,
  onOpenSettings
}) => {
  const tabs = [
    { id: 'compose', label: '✉️ Compose & Send' },
    { id: 'audience', label: '👥 Candidate Audience' },
    { id: 'history', label: '📊 Sent Campaigns' },
  ]

  return (
    <header className="app-header">
      <div className="brand-container">
        <span style={{ fontSize: '26px' }}>🎯</span>
        <div>
          <div className="brand-logo">SponsorAJobs</div>
        </div>
        <span className="brand-tag">Email Hub</span>

        {dryRun && (
          <span className="badge badge-dry-run" title="Dry-run enabled: No real emails sent">
            🧪 DRY RUN
          </span>
        )}
        {testMode && (
          <span className="badge badge-test-mode" title="Test mode active: Emails redirected to test recipient">
            🛡️ TEST MODE
          </span>
        )}
      </div>

      <nav className="nav-links">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          type="button"
          className="btn-settings-icon"
          onClick={onOpenSettings}
          title="Delivery & SMTP Settings"
        >
          ⚙️ Settings
        </button>
      </div>
    </header>
  )
}
