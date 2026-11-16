export interface Stream {
  id: number
  name: string
  parent_id: number | null
  momentum_score: number
  momentum_state: string
  category: string
  type: string
  priority_weight: number
  active: boolean
  description?: string | null
}

export interface CreateStreamPayload {
  name: string
  description?: string | null
  category?: 'weekday' | 'weekend' | 'everyday'
  type?: 'short_term' | 'long_term'
  parent_id?: number | null
}

export interface UpdateStreamPayload {
  name?: string
  description?: string | null
  category?: 'weekday' | 'weekend' | 'everyday'
  type?: 'short_term' | 'long_term'
  priority_weight?: number
  active?: boolean
}

export interface FocusRecommendation {
  stream_id: number
  stream_name: string
  parent_stream_name: string | null
  item_id: number | null
  action: string
  estimated_minutes: number | null
  momentum_score: number
  momentum_state: string
  recovery_mode: boolean
  first_step: string | null
  skip_count: number
}

export interface Dashboard {
  todays_focus: FocusRecommendation[]
}

export interface CaptureResult {
  item_id: number
  title: string
  item_type: string
  stream_id: number
  stream_name: string
}

export interface StreamSuggestionOption {
  stream_id: number
  stream_name: string
  confidence: number
  reason: string
}

export interface StreamSuggestion {
  status: 'confident' | 'ambiguous' | 'unavailable'
  recommended: StreamSuggestionOption | null
  options: StreamSuggestionOption[]
  reasoning: string
}

export interface Item {
  id: number
  stream_id: number
  title: string
  description: string | null
  notes: string | null
  url: string | null
  item_type: string
  status: string
  importance: string
  effort_estimate: string
  estimated_duration: number | null
  queue_position: number
  created_at: string
  updated_at: string
  last_accessed: string | null
  first_step: string | null
  skip_count: number
  snoozed_until: string | null
}

export interface UpdateItemPayload {
  stream_id?: number
  title?: string
  description?: string | null
  notes?: string | null
  url?: string | null
  item_type?: string
  status?: string
  importance?: string
  effort_estimate?: string
  estimated_duration?: number | null
}

export interface LessonRef {
  id: number
  title: string
}

export interface LabNeighbors {
  previous: LessonRef | null
  next: LessonRef | null
}

const API_BASE = '/api'

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    let message = `API error: ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) {
        message = typeof body.detail === 'string' ? body.detail : message
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(message)
  }
  if (res.status === 204) {
    return undefined as T
  }
  return res.json()
}

export const ITEMS_CSV_URL = `${API_BASE}/items/export.csv`

export const api = {
  getDashboard: () => fetchJson<Dashboard>('/dashboard'),
  getTodaysFocus: () => fetchJson<{ recommendations: FocusRecommendation[] }>('/focus/today'),
  getItems: () => fetchJson<Item[]>('/items'),
  getStreams: () => fetchJson<Stream[]>('/streams'),
  createStream: (payload: CreateStreamPayload) =>
    fetchJson<Stream>('/streams', { method: 'POST', body: JSON.stringify(payload) }),
  updateStream: (id: number, payload: UpdateStreamPayload) =>
    fetchJson<Stream>(`/streams/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteStream: (id: number) => fetchJson<void>(`/streams/${id}`, { method: 'DELETE' }),
  deleteItem: (id: number) => fetchJson<void>(`/items/${id}`, { method: 'DELETE' }),
  getItem: (id: number) => fetchJson<Item>(`/items/${id}`),
  getLabNeighbors: (id: number) => fetchJson<LabNeighbors>(`/items/${id}/lab-neighbors`),
  updateItem: (id: number, payload: UpdateItemPayload) =>
    fetchJson<Item>(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  reorderItem: (id: number, direction: 'up' | 'down') =>
    fetchJson<Item>(`/items/${id}/reorder`, {
      method: 'POST',
      body: JSON.stringify({ direction }),
    }),
  ensureFirstStep: (id: number) => fetchJson<Item>(`/items/${id}/first-step`, { method: 'POST' }),
  logProgress: (id: number, notes: string | null) =>
    fetchJson<Item>(`/items/${id}/progress`, { method: 'POST', body: JSON.stringify({ notes }) }),
  snoozeItem: (id: number, days: number, notes: string | null) =>
    fetchJson<Item>(`/items/${id}/snooze`, { method: 'POST', body: JSON.stringify({ days, notes }) }),
  splitItem: (id: number) => fetchJson<Item[]>(`/items/${id}/split`, { method: 'POST' }),
  suggestStream: (content: string) =>
    fetchJson<StreamSuggestion>('/capture/suggest-stream', {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  capture: (content: string, streamId: number) =>
    fetchJson<CaptureResult>('/capture', {
      method: 'POST',
      body: JSON.stringify({ content, stream_id: streamId }),
    }),
}
