import { useState } from 'react'
import { Narrative, fetchNarrative, regenerateNarrative } from '../api'

interface Props {
  alertId: string
}

export default function NarrativePanel({ alertId }: Props) {
  const [narrative, setNarrative] = useState<Narrative | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const n = await fetchNarrative(alertId)
      setNarrative(n)
    } catch {
      setError('Failed to load narrative')
    } finally {
      setLoading(false)
    }
  }

  const regenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      const n = await regenerateNarrative(alertId)
      setNarrative(n)
    } catch {
      setError('Regeneration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2">
        <button
          onClick={load}
          disabled={loading}
          className="text-xs bg-primary hover:bg-primary/80 text-primary-foreground px-3 py-1.5 rounded disabled:opacity-50 transition-colors"
        >
          {loading ? 'Generating…' : narrative ? 'Refresh' : '✦ Generate Narrative'}
        </button>
        {narrative && (
          <button
            onClick={regenerate}
            disabled={loading}
            className="text-xs bg-secondary hover:bg-accent text-foreground px-3 py-1.5 rounded disabled:opacity-50 transition-colors"
          >
            ↻ Regenerate
          </button>
        )}
        {narrative && (
          <span className="text-xs text-muted-foreground">
            Model: {narrative.model_version}
          </span>
        )}
      </div>

      {error && <div className="text-destructive text-sm">{error}</div>}

      {narrative && (
        <div className="prose prose-invert prose-sm max-w-none">
          <div className="text-sm text-foreground whitespace-pre-wrap leading-relaxed bg-card border border-border rounded p-4">
            {narrative.content}
          </div>
        </div>
      )}

      {!narrative && !loading && (
        <div className="text-muted-foreground text-sm">
          Click "Generate Narrative" to produce an AI-written investigation memo for this alert.
        </div>
      )}
    </div>
  )
}
