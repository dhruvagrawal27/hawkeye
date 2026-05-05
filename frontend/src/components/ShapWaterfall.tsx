import { RiskFactor } from '../api'

interface Props {
  factors: RiskFactor[]
}

export default function ShapWaterfall({ factors }: Props) {
  if (!factors || factors.length === 0) {
    return (
      <div className="text-muted-foreground text-sm p-4">No SHAP data available.</div>
    )
  }

  const maxAbs = Math.max(...factors.map((f) => Math.abs(f.contribution)), 0.001)

  return (
    <div className="space-y-2 p-4">
      <h3 className="text-sm font-semibold text-foreground mb-3">SHAP Attribution — Top Factors</h3>
      {factors.map((f) => {
        const pct = (Math.abs(f.contribution) / maxAbs) * 100
        const isPositive = f.contribution > 0
        return (
          <div key={f.feature} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-foreground">{f.plain_name}</span>
              <span className={isPositive ? 'text-red-400' : 'text-green-400'}>
                {isPositive ? '+' : ''}
                {f.contribution.toFixed(4)}
              </span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  isPositive ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
