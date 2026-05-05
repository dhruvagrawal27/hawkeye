import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Alert, fetchAlerts } from '../api'
import { formatDistanceToNow } from 'date-fns'

interface Props {
  alerts: Alert[]
}

const SEVERITY_CLASSES: Record<string, string> = {
  critical: 'border-l-4 border-red-500 bg-red-500/5',
  high: 'border-l-4 border-orange-500 bg-orange-500/5',
  medium: 'border-l-4 border-yellow-500 bg-yellow-500/5',
  low: 'border-l-4 border-green-500 bg-green-500/5',
}

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/20 px-2 py-0.5 rounded text-xs font-semibold uppercase',
  high: 'text-orange-400 bg-orange-500/20 px-2 py-0.5 rounded text-xs font-semibold uppercase',
  medium: 'text-yellow-400 bg-yellow-500/20 px-2 py-0.5 rounded text-xs font-semibold uppercase',
  low: 'text-green-400 bg-green-500/20 px-2 py-0.5 rounded text-xs font-semibold uppercase',
}

export default function AlertFeed({ alerts }: Props) {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<string>('all')

  const filtered = filter === 'all' ? alerts : alerts.filter((a) => a.severity === filter)

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h2 className="font-semibold text-sm text-foreground">Live Alert Feed</h2>
        <div className="flex gap-1">
          {['all', 'critical', 'high', 'medium'].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                filter === s
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
            No alerts yet. Start the replay to see live events.
          </div>
        ) : (
          filtered.map((alert) => (
            <div
              key={alert.id}
              className={`px-4 py-3 border-b border-border cursor-pointer hover:bg-accent/50 transition-colors ${
                SEVERITY_CLASSES[alert.severity] || ''
              }`}
              onClick={() => navigate(`/employees/${alert.employee_id}`)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm text-foreground truncate">
                      {alert.employee_id}
                    </span>
                    <span className={SEVERITY_BADGE[alert.severity] || ''}>
                      {alert.severity}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mb-1">
                    Score:{' '}
                    <span className="text-foreground font-semibold">
                      {alert.score.toFixed(3)}
                    </span>{' '}
                    · Threshold: {alert.threshold.toFixed(3)}
                  </div>
                  {alert.risk_factors.slice(0, 2).map((f) => (
                    <div key={f.feature} className="text-xs text-muted-foreground">
                      <span className="text-foreground">{f.plain_name}</span>:{' '}
                      <span
                        className={f.contribution > 0 ? 'text-red-400' : 'text-green-400'}
                      >
                        {f.contribution > 0 ? '+' : ''}
                        {f.contribution.toFixed(4)}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
