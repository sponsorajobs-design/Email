import React, { useState, useEffect } from 'react'
import { DashboardStats, SystemHealth } from './types'
import { api } from './services/api'
import { Navbar } from './components/Navbar'
import { ComposeFlow } from './components/ComposeFlow'
import { AudienceDirectoryPage } from './pages/AudienceDirectoryPage'
import { CampaignHistoryPage } from './pages/CampaignHistoryPage'
import { SimpleSettingsModal } from './components/SimpleSettingsModal'

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('compose')
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [selectedComposeCategory, setSelectedComposeCategory] = useState<string | null>(null)
  const [showSettingsModal, setShowSettingsModal] = useState(false)

  const refreshGlobalData = async () => {
    try {
      const [s, h] = await Promise.all([
        api.getStats(),
        api.getHealth()
      ])
      setStats(s)
      setHealth(h)
    } catch (e) {
      console.error('Failed to load initial metrics:', e)
    }
  }

  useEffect(() => {
    refreshGlobalData()
  }, [])

  const handleComposeToCategory = (categoryName: string) => {
    setSelectedComposeCategory(categoryName)
    setActiveTab('compose')
  }

  return (
    <div>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        dryRun={stats?.dry_run_mode ?? true}
        testMode={stats?.email_test_mode ?? true}
        onOpenSettings={() => setShowSettingsModal(true)}
      />

      <main className="main-container">
        {activeTab === 'compose' && (
          <ComposeFlow
            stats={stats}
            initialCategory={selectedComposeCategory}
            onCampaignCreated={() => {
              refreshGlobalData()
            }}
            onOpenSettings={() => setShowSettingsModal(true)}
          />
        )}

        {activeTab === 'audience' && (
          <AudienceDirectoryPage
            onComposeToCategory={handleComposeToCategory}
          />
        )}

        {activeTab === 'history' && (
          <CampaignHistoryPage
            onComposeNew={() => {
              setSelectedComposeCategory(null)
              setActiveTab('compose')
            }}
          />
        )}
      </main>

      <SimpleSettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        onUpdate={refreshGlobalData}
        stats={stats}
        health={health}
      />
    </div>
  )
}

export default App
