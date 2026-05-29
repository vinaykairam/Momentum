import { CaptureBox } from '@/components/CaptureBox'
import { FocusCard } from '@/components/FocusCard'
import { FocusMode } from '@/components/FocusMode'
import { MomentumBar } from '@/components/MomentumBar'
import { Card, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, TrendingUp } from 'lucide-react'

function AlertIcon({ severity }: { severity: string }) {
  if (severity === 'positive') return <TrendingUp className="h-4 w-4 text-thriving" />
  if (severity === 'critical') return <AlertTriangle className="h-4 w-4 text-critical" />
  return <AlertTriangle className="h-4 w-4 text-neglected" />
}

export function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
    refetchInterval: 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-pulse rounded-full bg-accent/20" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="py-20 text-center text-muted">
        <p className="text-lg">Unable to connect to Momentum Engine</p>
        <p className="mt-2 text-sm">Start the backend: uvicorn app.main:app --reload</p>
      </div>
    )
  }

  const [primary, ...rest] = data.todays_focus
  const nextFocus = rest[0] ?? null

  return (
    <>
      <FocusMode nextFocus={nextFocus} />

      <div className="mx-auto max-w-3xl px-6 py-12 md:py-16">
        <motion.header
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-16 flex items-end justify-between"
        >
          <div>
            <p className="mb-2 text-sm text-muted">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
            </p>
            <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">Momentum</h1>
          </div>
          <CaptureBox />
        </motion.header>

        <section className="mb-16">
          <h2 className="mb-6 text-xs font-medium uppercase tracking-[0.2em] text-muted">
            Today&apos;s Focus
          </h2>
          <div className="space-y-4">
            {primary && <FocusCard focus={primary} index={0} featured />}
            {rest.map((focus, i) => (
              <FocusCard key={`${focus.stream_id}-${focus.item_id}`} focus={focus} index={i + 1} />
            ))}
          </div>
        </section>

        <section className="mb-16">
          <Card>
            <CardTitle className="mb-6">Momentum Health</CardTitle>
            <div className="space-y-5">
              {data.streams.map((stream) => (
                <MomentumBar
                  key={stream.id}
                  name={stream.name}
                  score={stream.momentum_score}
                  state={stream.momentum_state}
                />
              ))}
            </div>
          </Card>
        </section>

        {data.alerts.length > 0 && (
          <section className="mb-16">
            <Card>
              <CardTitle className="mb-4">Momentum Alerts</CardTitle>
              <ul className="space-y-3">
                {data.alerts.map((alert) => (
                  <li key={alert.stream_id} className="flex items-start gap-3 text-sm">
                    <AlertIcon severity={alert.severity} />
                    <span>{alert.message}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </section>
        )}

        {data.recent_progress.length > 0 && (
          <section>
            <Card>
              <CardTitle className="mb-4">Recent Progress</CardTitle>
              <ul className="space-y-3">
                {data.recent_progress.map((item) => (
                  <li key={item.item_id} className="flex items-center gap-3 text-sm">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-thriving" />
                    <span>{item.title}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </section>
        )}
      </div>
    </>
  )
}
