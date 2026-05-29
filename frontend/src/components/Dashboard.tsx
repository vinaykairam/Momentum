import { CaptureBox } from '@/components/CaptureBox'
import { TodaysFocus } from '@/components/TodaysFocus'
import { FocusMode } from '@/components/FocusMode'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { GitBranch, List } from 'lucide-react'

interface DashboardProps {
  onViewItems?: () => void
  onViewStreams?: () => void
}

const ease = [0.22, 1, 0.36, 1] as const

export function Dashboard({ onViewItems, onViewStreams }: DashboardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
    refetchInterval: 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          className="h-2.5 w-2.5 rounded-full bg-accent/40"
        />
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

  const nextFocus = data.todays_focus[1] ?? null

  return (
    <>
      <FocusMode nextFocus={nextFocus} />

      <div className="mx-auto max-w-2xl px-5 py-10 md:px-8 md:py-14">
        <motion.header
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease }}
          className="mb-10 flex items-center justify-between gap-4"
        >
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Today</h1>
          <div className="flex shrink-0 items-center gap-1">
            {onViewStreams && (
              <Button variant="ghost" size="sm" onClick={onViewStreams} className="gap-1.5 text-muted">
                <GitBranch className="h-4 w-4" />
                Streams
              </Button>
            )}
            {onViewItems && (
              <Button variant="ghost" size="sm" onClick={onViewItems} className="gap-1.5 text-muted">
                <List className="h-4 w-4" />
                Items
              </Button>
            )}
            <CaptureBox />
          </div>
        </motion.header>

        <TodaysFocus focus={data.todays_focus} />
      </div>
    </>
  )
}
