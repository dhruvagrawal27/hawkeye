import axios from 'axios'
import keycloak from '../lib/auth'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({ baseURL: BASE })

// Attach Keycloak JWT to every request on this instance
api.interceptors.request.use(async (config) => {
  if (keycloak.authenticated) {
    try {
      // Refresh if expiring within 30s
      await keycloak.updateToken(30)
    } catch {
      // Token refresh failed — let the request go; backend will return 401
    }
    if (keycloak.token) {
      config.headers.set('Authorization', `Bearer ${keycloak.token}`)
    }
  }
  return config
})

// Types
export interface RiskFactor {
  feature: string
  contribution: number
  plain_name: string
}

export interface Alert {
  id: string
  employee_id: string
  score: number
  m1_score?: number
  m2_score?: number
  threshold: number
  severity: 'low' | 'medium' | 'high' | 'critical'
  risk_factors: RiskFactor[]
  status: string
  created_at: string
  updated_at: string
}

export interface Employee {
  id: string
  account_id?: string
  department?: string
  role?: string
  risk_score: number
  last_seen?: string
}

export interface Narrative {
  id: string
  alert_id: string
  model_version: string
  content: string
  shap_footer?: string
  generated_at: string
}

export interface ReplayStatus {
  running: boolean
  paused: boolean
  rate: number
  events_published: number
  events_consumed: number
  alerts_created: number
}

export interface GraphData {
  nodes: Array<{ id: string; label: string; type: string; risk_score?: number; flagged?: boolean }>
  links: Array<{ source: string; target: string; weight: number; access_type?: string }>
}

// API calls
export const fetchAlerts = (params?: Record<string, string | number>) =>
  api.get<Alert[]>('/alerts', { params }).then((r) => r.data)

export const fetchAlert = (id: string) =>
  api.get<Alert>(`/alerts/${id}`).then((r) => r.data)

export const fetchEmployees = () =>
  api.get<Employee[]>('/employees').then((r) => r.data)

export const fetchEmployee = (id: string) =>
  api.get<Employee>(`/employees/${id}`).then((r) => r.data)

export const fetchEmployeeAlerts = (id: string) =>
  api.get<Alert[]>(`/employees/${id}/alerts`).then((r) => r.data)

export const fetchNarrative = (alertId: string) =>
  api.get<Narrative>(`/narrative/${alertId}`).then((r) => r.data)

export const regenerateNarrative = (alertId: string) =>
  api.post<Narrative>(`/narrative/${alertId}/regenerate`).then((r) => r.data)

export const fetchGraph = (employeeId?: string, depth = 2) =>
  employeeId
    ? api.get<GraphData>(`/graph/${employeeId}?depth=${depth}`).then((r) => r.data)
    : api.get<GraphData>('/graph').then((r) => r.data)

export const controlReplay = (action: string, rate?: number) =>
  api.post<ReplayStatus>('/events/replay', { action, rate }).then((r) => r.data)

export const fetchReplayStatus = () =>
  api.get<ReplayStatus>('/events/replay/status').then((r) => r.data)

export const triageAlert = (alertId: string, action_type: string, notes?: string) =>
  api.post(`/alerts/${alertId}/triage`, { action_type, notes }).then((r) => r.data)
