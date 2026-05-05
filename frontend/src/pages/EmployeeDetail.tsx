import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  fetchEmployee, fetchEmployeeAlerts, fetchAlert,
  Employee, Alert,
} from '../api'
import ShapWaterfall from '../components/ShapWaterfall'
import GraphCanvas from '../components/GraphCanvas'
import NarrativePanel from '../components/NarrativePanel'
import { formatDistanceToNow } from 'date-fns'

type Tab = 'timeline' | 'shap' | 'graph' | 'narrative'

export default function EmployeeDetail() {
  const { id } = useParams<{ id: string }>()
  const [employee, setEmployee] = useState<Employee | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [tab, setTab] = useState<Tab>('timeline')

  useEffect(() => {
    if (!id) return
    fetchEmployee(id).then(setEmployee).catch(console.error)
    fetchEmployeeAlerts(id).then((a) => {
      setAlerts(a)
      if (a.length > 0) setSelectedAlert(a[0])
    }).catch(console.error)
  }, [id])

  const TABS: { key: Tab; label: string }[] = [
    { key: 'timeline', label: 'Timeline' },
    { key: 'shap', label: 'SHAP Factors' },
    { key: 'graph', label: 'Graph' },
    { key: 'narrative', label: 'Narrative' },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-3 flex items-center gap-4">
        <Link to="/" className="text-muted-foreground hover:text-foreground text-sm">
          ← Dashboard
        </Link>
        <div className="text-lg font-bold text-primary">HAWKEYE</div>
        {employee && (
          <div className="flex items-center gap-3 ml-4">
            <span className="font-mono text-foreground">{employee.id}</span>
            {employee.department && (
              <span className="text-muted-foreground text-sm">{employee.department}</span>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded font-semibold ${
                employee.risk_score >= 0.7
                  ? 'bg-red-500/20 text-red-400'
                  : employee.risk_score >= 0.5
                  ? 'bg-orange-500/20 text-orange-400'
                  : 'bg-secondary text-muted-foreground'
              }`}
            >
              Risk: {employee.risk_score.toFixed(3)}
            </span>
          </div>
        )}
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 h-[calc(100vh-56px)]">
        {/* Alert list */}
        <div className="border-r border-border overflow-y-auto">
          <div className="px-4 py-3 border-b border-border">
            <h2 className="font-semibold text-sm">Alerts ({alerts.length})</h2>
          </div>
          {alerts.map((a) => (
            <div
              key={a.id}
              onClick={() => setSelectedAlert(a)}
              className={`px-4 py-3 border-b border-border cursor-pointer hover:bg-accent/50 transition-colors ${
                selectedAlert?.id === a.id ? 'bg-accent/30' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span
                  className={`text-xs px-1.5 py-0.5 rounded uppercase font-semibold ${
                    a.severity === 'critical'
                      ? 'text-red-400 bg-red-500/20'
                      : a.severity === 'high'
                      ? 'text-orange-400 bg-orange-500/20'
                      : 'text-yellow-400 bg-yellow-500/20'
                  }`}
                >
                  {a.severity}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                </span>
              </div>
              <div className="text-sm font-semibold mt-1">Score: {a.score.toFixed(3)}</div>
            </div>
          ))}
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-2 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="border-b border-border flex">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-4 py-3 text-sm transition-colors ${
                  tab === t.key
                    ? 'border-b-2 border-primary text-foreground font-medium'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto">
            {tab === 'timeline' && (
              <div className="p-4 space-y-3">
                {alerts.map((a) => (
                  <div key={a.id} className="border border-border rounded p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground">
                        {new Date(a.created_at).toLocaleString()}
                      </span>
                      <span className={`text-xs uppercase font-semibold ${
                        a.severity === 'critical' ? 'text-red-400'
                        : a.severity === 'high' ? 'text-orange-400'
                        : 'text-yellow-400'
                      }`}>{a.severity}</span>
                    </div>
                    <div className="text-sm">
                      Score: <strong>{a.score.toFixed(3)}</strong> · M1: {a.m1_score?.toFixed(3)} · M2: {a.m2_score?.toFixed(3)}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Status: {a.status}</div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'shap' && selectedAlert && (
              <ShapWaterfall factors={selectedAlert.risk_factors} />
            )}

            {tab === 'graph' && id && (
              <GraphCanvas employeeId={id} height={500} />
            )}

            {tab === 'narrative' && selectedAlert && (
              <NarrativePanel alertId={selectedAlert.id} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
