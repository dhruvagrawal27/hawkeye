import { useState } from 'react'
import { ReplayStatus, controlReplay } from '../api'

interface Props {
  replay: ReplayStatus | null
  onUpdate: (s: ReplayStatus) => void
}

export default function ReplayControls({ replay, onUpdate }: Props) {
  const [rate, setRate] = useState(200)
  const [loading, setLoading] = useState(false)

  const act = async (action: string) => {
    setLoading(true)
    try {
      const s = await controlReplay(action, action === 'start' ? rate : undefined)
      onUpdate(s)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const running = replay?.running && !replay?.paused

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground hidden md:block">Replay:</span>
      <input
        type="range"
        min={10}
        max={5000}
        step={10}
        value={rate}
        onChange={(e) => setRate(Number(e.target.value))}
        className="w-20 h-1 accent-primary"
        title={`${rate} ev/s`}
      />
      <span className="text-xs text-muted-foreground w-14">{rate} ev/s</span>

      {!replay?.running ? (
        <button
          onClick={() => act('start')}
          disabled={loading}
          className="text-xs bg-green-600 hover:bg-green-500 text-white px-3 py-1.5 rounded transition-colors disabled:opacity-50"
        >
          ▶ Start
        </button>
      ) : (
        <>
          <button
            onClick={() => act('pause')}
            disabled={loading}
            className="text-xs bg-yellow-600 hover:bg-yellow-500 text-white px-3 py-1.5 rounded transition-colors disabled:opacity-50"
          >
            {replay.paused ? '▶ Resume' : '⏸ Pause'}
          </button>
          <button
            onClick={() => act('stop')}
            disabled={loading}
            className="text-xs bg-red-700 hover:bg-red-600 text-white px-3 py-1.5 rounded transition-colors disabled:opacity-50"
          >
            ⏹ Stop
          </button>
        </>
      )}
    </div>
  )
}
