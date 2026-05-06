import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAlerts, Alert, fetchReplayStatus, controlReplay, ReplayStatus } from '../api'
import { getUsername, logout } from '../lib/auth'
import GraphCanvas from '../components/GraphCanvas'
import ReplayControls from '../components/ReplayControls'
import AlertFeed from '../components/AlertFeed'

export default function Dashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [replay, setReplay] = useState<ReplayStatus | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const loadAlerts = () => {
    fetchAlerts({ limit: 50 }).then(setAlerts).catch(console.error)
  }

  useEffect(() => {
    loadAlerts()
    const alertInterval = setInterval(loadAlerts, 5000)

    // WebSocket for live push
    const wsBase = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
    const ws = new WebSocket(`${wsBase}/ws/alerts`)
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'alert') {
          loadAlerts()
        }
      } catch {}
    }
    ws.onerror = () => {}

    // Poll replay status every 3s to keep live indicator accurate
    fetchReplayStatus().then(setReplay).catch(() => {})
    const replayInterval = setInterval(() => {
      fetchReplayStatus().then(setReplay).catch(() => {})
    }, 3000)

    return () => {
      clearInterval(alertInterval)
      clearInterval(replayInterval)
      ws.close()
    }
  }, [])

  const criticalCount = alerts.filter((a) => a.severity === 'critical').length
  const highCount = alerts.filter((a) => a.severity === 'high').length
  const lastHourCount = alerts.filter(
    (a) => Date.now() - new Date(a.created_at).getTime() < 3_600_000
  ).length

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="text-xl font-bold text-primary">🦅 HAWKEYE</div>
          <span className="text-xs text-muted-foreground hidden sm:block">
            Every Action Leaves a Trace
          </span>
        </div>
        <div className="flex items-center gap-4">
          <ReplayControls replay={replay} onUpdate={setReplay} />
          <button
            onClick={logout}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {getUsername()} · Sign out
          </button>
        </div>
      </header>

      {/* Stats bar */}
      <div className="px-6 py-3 border-b border-border flex gap-6 text-sm">
        <div>
          <span className="text-muted-foreground">Alerts (last hour): </span>
          <span className="font-semibold text-foreground">{lastHourCount}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Critical: </span>
          <span className="font-semibold text-red-400">{criticalCount}</span>
        </div>
        <div>
          <span className="text-muted-foreground">High: </span>
          <span className="font-semibold text-orange-400">{highCount}</span>
        </div>
        {replay?.running && (
          <div className="flex items-center gap-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <span className="text-green-400">{replay.rate} ev/s</span>
            {replay.events_published > 0 && (
              <span className="text-muted-foreground text-xs ml-2">
                {replay.events_published.toLocaleString()} events published
              </span>
            )}
          </div>
        )}
        {!replay?.running && (
          <div className="text-xs text-muted-foreground italic">
            ▶ Press Start to begin live replay
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 h-[calc(100vh-120px)]">
        <div className="border-r border-border overflow-y-auto">
          <AlertFeed alerts={alerts} />
        </div>
        <div className="overflow-hidden">
          <GraphCanvas employeeId={undefined} height={600} />
        </div>
      </div>
    </div>
  )
}
