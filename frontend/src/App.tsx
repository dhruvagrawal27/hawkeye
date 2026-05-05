import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { initAuth } from './lib/auth'
import Dashboard from './pages/Dashboard'
import EmployeeDetail from './pages/EmployeeDetail'

export default function App() {
  const [ready, setReady] = useState(false)
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    initAuth().then((ok) => {
      setAuthed(ok)
      setReady(true)
    })
  }, [])

  if (!ready) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl font-bold text-primary mb-2">HAWKEYE</div>
          <div className="text-muted-foreground text-sm animate-pulse">Authenticating…</div>
        </div>
      </div>
    )
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-destructive">Authentication failed. Redirecting…</div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/employees/:id" element={<EmployeeDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
