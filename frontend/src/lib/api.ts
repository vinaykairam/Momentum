export interface Stream {
  id: number
  name: string
  momentum_score: number
  momentum_state: string
  category: string
}

export interface FocusRecommendation {
  stream_id: number
  stream_name: string
  item_id: number | null
  action: string
  estimated_minutes: number | null
  momentum_score: number
  momentum_state: string
  recovery_mode: boolean
}

export interface MomentumAlert {
  stream_id: number
  stream_name: string
  message: string
  severity: 'critical' | 'warning' | 'positive'
  momentum_score: number
}

export interface RecentProgress {
  item_id: number
  title: string
  stream_id: number
  completed_at: string | null
}

export interface Dashboard {
  todays_focus: FocusRecommendation[]
  streams: Stream[]
  alerts: MomentumAlert[]
  recent_progress: RecentProgress[]
}

export interface CaptureResult {
  item_id: number
  title: string
  item_type: string
  suggested_stream_id: number | null
  suggested_stream_name: string | null
  confidence: number
  summary: string | null
}

const API_BASE = '/api'

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  return res.json()
}

export const api = {
  getDashboard: () => fetchJson<Dashboard>('/dashboard'),
  getTodaysFocus: () => fetchJson<{ recommendations: FocusRecommendation[] }>('/focus/today'),
  capture: (content: string) =>
    fetchJson<CaptureResult>('/capture', {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
}
