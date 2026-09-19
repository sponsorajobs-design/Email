import {
  DashboardStats,
  SystemHealth,
  Job,
  Subscriber,
  Match,
  Campaign,
  CampaignPreviewItem,
  CampaignSubscriberItem,
  CampaignCompositionDetail,
  EmailQueueItem,
  AuditLog,
  SubscriberSentEmailHistoryItem,
  CategorySummary,
  AudienceCategory,
  CustomPreviewRequest,
  CustomPreviewResponse,
  DirectComposeSendRequest
} from '../types'

const BASE_URL = '/api'

export async function handleResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')

  if (!res.ok) {
    let errorMessage = `HTTP ${res.status}: ${res.statusText}`
    if (isJson) {
      try {
        const errorData = await res.json()
        errorMessage = errorData.detail || errorData.message || JSON.stringify(errorData)
      } catch {
        // fallback
      }
    } else {
      try {
        const text = await res.text()
        if (text) {
          errorMessage = text.length > 300 ? `${text.slice(0, 300)}...` : text
        }
      } catch {
        // fallback
      }
    }
    throw new Error(errorMessage)
  }

  if (isJson) {
    return res.json()
  }
  const text = await res.text()
  return text as unknown as T
}

async function fetchApi<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  return handleResponse<T>(res)
}

export const api = {
  // Health & Stats
  getHealth: async (): Promise<SystemHealth> => {
    return fetchApi<SystemHealth>(`${BASE_URL}/health`)
  },
  getStats: async (): Promise<DashboardStats> => {
    return fetchApi<DashboardStats>(`${BASE_URL}/dashboard/stats`)
  },

  // Sync
  testSupabaseConnection: async () => {
    const res = await fetch(`${BASE_URL}/sync/test-connection`, { method: 'POST' })
    return res.json()
  },
  syncSubscribers: async () => {
    const res = await fetch(`${BASE_URL}/sync/subscribers`, { method: 'POST' })
    return res.json()
  },
  syncJobs: async () => {
    const res = await fetch(`${BASE_URL}/sync/jobs`, { method: 'POST' })
    return res.json()
  },

  // Jobs
  getJobs: async (status?: string): Promise<Job[]> => {
    const url = status ? `${BASE_URL}/jobs?status=${status}` : `${BASE_URL}/jobs`
    const res = await fetch(url)
    return res.json()
  },
  verifyJobLinks: async (force: boolean = false) => {
    const res = await fetch(`${BASE_URL}/jobs/verify?force=${force}`, { method: 'POST' })
    return res.json()
  },

  // Subscribers
  getSubscribers: async (search?: string, category?: string, limit: number = 1000): Promise<Subscriber[]> => {
    const params = new URLSearchParams()
    if (search) params.append('search', search)
    if (category && category.toLowerCase() !== 'all') params.append('category', category)
    params.append('limit', limit.toString())
    const queryStr = params.toString() ? `?${params.toString()}` : ''
    const res = await fetch(`${BASE_URL}/subscribers${queryStr}`)
    return res.json()
  },
  getCategories: async (): Promise<CategorySummary[]> => {
    const res = await fetch(`${BASE_URL}/subscribers/categories`)
    return res.json()
  },
  getSubscriberHistory: async (id: number): Promise<SubscriberSentEmailHistoryItem[]> => {
    const res = await fetch(`${BASE_URL}/subscribers/${id}/history`)
    return res.json()
  },
  sendCategoryCampaign: async (payload: { category: string; match_threshold?: number; batch_size?: number; auto_send?: boolean }) => {
    const res = await fetch(`${BASE_URL}/campaigns/send-category`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    return res.json()
  },

  // Audience Directory & Direct Compose API
  getAudienceDirectory: async (): Promise<AudienceCategory[]> => {
    return fetchApi<AudienceCategory[]>(`${BASE_URL}/campaigns/audience-directory`)
  },
  previewCustomEmail: async (payload: CustomPreviewRequest): Promise<CustomPreviewResponse> => {
    return fetchApi<CustomPreviewResponse>(`${BASE_URL}/campaigns/preview-custom`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
  },
  directSendCampaign: async (payload: DirectComposeSendRequest): Promise<any> => {
    return fetchApi<any>(`${BASE_URL}/campaigns/direct-send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
  },


  // Matching
  runMatching: async (threshold?: number) => {
    const url = threshold ? `${BASE_URL}/matching/run?threshold=${threshold}` : `${BASE_URL}/matching/run`
    const res = await fetch(url, { method: 'POST' })
    return res.json()
  },
  getMatches: async (minScore: number = 0): Promise<Match[]> => {
    const res = await fetch(`${BASE_URL}/matching/matches?min_score=${minScore}`)
    return res.json()
  },

  // Campaigns & Email Control Center
  getCampaigns: async (): Promise<Campaign[]> => {
    return fetchApi<Campaign[]>(`${BASE_URL}/admin/campaigns`)
  },
  getCampaign: async (id: number): Promise<Campaign> => {
    return fetchApi<Campaign>(`${BASE_URL}/admin/campaigns/${id}`)
  },
  createCampaign: async (payload: { name: string; match_threshold?: number; batch_size?: number; notes?: string }): Promise<Campaign> => {
    return fetchApi<Campaign>(`${BASE_URL}/admin/campaigns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
  },
  getCampaignSubscribers: async (id: number, limit: number = 200, offset: number = 0): Promise<CampaignSubscriberItem[]> => {
    return fetchApi<CampaignSubscriberItem[]>(`${BASE_URL}/admin/campaigns/${id}/subscribers?limit=${limit}&offset=${offset}`)
  },
  getCampaignComposition: async (campaignId: number, compositionId: number): Promise<CampaignCompositionDetail> => {
    return fetchApi<CampaignCompositionDetail>(`${BASE_URL}/admin/campaigns/${campaignId}/compositions/${compositionId}`)
  },
  getCampaignPreview: async (id: number): Promise<CampaignPreviewItem[]> => {
    return fetchApi<CampaignPreviewItem[]>(`${BASE_URL}/campaigns/${id}/preview`)
  },
  dispatchCampaign: async (id: number, batchLimit: number = 50) => {
    return fetchApi<any>(`${BASE_URL}/admin/campaigns/${id}/dispatch?batch_limit=${batchLimit}`, { method: 'POST' })
  },
  approveCampaign: async (id: number) => {
    return fetchApi<any>(`${BASE_URL}/campaigns/${id}/approve`, { method: 'POST' })
  },
  sendCampaign: async (id: number, batchLimit: number = 50) => {
    return fetchApi<any>(`${BASE_URL}/admin/campaigns/${id}/dispatch?batch_limit=${batchLimit}`, { method: 'POST' })
  },
  cancelCampaign: async (id: number) => {
    return fetchApi<any>(`${BASE_URL}/admin/campaigns/${id}/cancel`, { method: 'POST' })
  },
  sendSingleCampaignItem: async (campaignId: number, queueId: number) => {
    return fetchApi<any>(`${BASE_URL}/admin/campaigns/${campaignId}/items/${queueId}/send`, { method: 'POST' })
  },
  sendSelectedCampaignItems: async (campaignId: number, queueIds: number[]) => {
    return fetchApi<any>(`${BASE_URL}/admin/campaigns/${campaignId}/send-selected`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ queue_ids: queueIds })
    })
  },

  // Email Test & Queue
  sendTestEmail: async (payload: any) => {
    const res = await fetch(`${BASE_URL}/email/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    return res.json()
  },
  getEmailQueue: async (status?: string): Promise<EmailQueueItem[]> => {
    const url = status ? `${BASE_URL}/email/queue?status=${status}` : `${BASE_URL}/email/queue`
    const res = await fetch(url)
    return res.json()
  },

  // Logs & Settings
  getAuditLogs: async (): Promise<AuditLog[]> => {
    const res = await fetch(`${BASE_URL}/audit-logs`)
    return res.json()
  },
  getSettings: async () => {
    const res = await fetch(`${BASE_URL}/settings`)
    return res.json()
  },
  updateSettings: async (payload: any) => {
    const res = await fetch(`${BASE_URL}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    return res.json()
  }
}
