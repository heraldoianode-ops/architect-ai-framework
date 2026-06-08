import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
}

export interface SummaryKPIs {
  total_clients: number
  hot_leads: number
  total_properties: number
  interactions_this_week: number
  closed_this_month: number
}

export const analyticsApi = {
  summary: () => api.get<SummaryKPIs>('/analytics/summary'),
  funnel: () => api.get('/analytics/funnel'),
  activity: (days = 30) => api.get(`/analytics/activity?days=${days}`),
  agents: () => api.get('/analytics/agents'),
  properties: () => api.get('/analytics/properties'),
  forecast: () => api.get('/analytics/forecast'),
}

export interface ClientCard {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  lead_stage: string
  lead_score: number | null
  source: string
}

export interface KanbanColumn {
  stage: string
  clients: ClientCard[]
}

export const crmApi = {
  kanban: () => api.get<KanbanColumn[]>('/crm/kanban'),
  search: (q: string) => api.get<ClientCard[]>(`/crm/search?q=${encodeURIComponent(q)}`),
  updateStage: (id: string, stage: string) =>
    api.patch(`/clients/${id}/stage`, { stage }),
  getInteractions: (id: string) => api.get(`/clients/${id}/interactions`),
  addInteraction: (id: string, body: object) =>
    api.post(`/clients/${id}/interactions`, body),
  getSummary: (id: string) => api.get(`/clients/${id}/summary`),
}

export const matchingApi = {
  forClient: (id: string, topK = 10) =>
    api.get(`/matching/clients/${id}/properties?top_k=${topK}`),
  byQuery: (query: string, topK = 10) =>
    api.post('/matching/query', { query_text: query, top_k: topK }),
  updatePreferences: (id: string, prefs: object) =>
    api.patch(`/matching/clients/${id}/preferences`, prefs),
}

export const scrapingApi = {
  listSources: () => api.get('/admin/scraping/sources'),
  createSource: (body: object) => api.post('/admin/scraping/sources', body),
  updateSource: (id: string, body: object) =>
    api.patch(`/admin/scraping/sources/${id}`, body),
  deleteSource: (id: string) => api.delete(`/admin/scraping/sources/${id}`),
  runSource: (id: string) => api.post(`/admin/scraping/sources/${id}/run`),
  resetCircuitBreaker: (id: string) =>
    api.post(`/admin/circuit-breaker/${id}/reset`),
}

export const ragApi = {
  list: () => api.get('/rag/documents'),
  ingest: (body: object) => api.post('/rag/documents', body),
  delete: (id: string) => api.delete(`/rag/documents/${id}`),
  query: (query: string, topK = 5) =>
    api.post('/rag/query', { query, top_k: topK }),
}

export const predictionsApi = {
  scoreClient: (id: string) => api.get(`/predictions/clients/${id}`),
  batchScore: (ids: string[]) =>
    api.post('/predictions/clients/batch', { client_ids: ids }),
  train: () => api.post('/predictions/train'),
}

export default api
