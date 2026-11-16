import { CaptureBox } from '@/components/CaptureBox'
import { TodaysFocus } from '@/components/TodaysFocus'
import { FocusMode } from '@/components/FocusMode'
import { PageLoading, PageShell } from '@/components/PageShell'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { GitBranch, List } from 'lucide-react'

interface DashboardProps {
  onViewItems?: () => void
  onViewStreams?: () => void
}

export function Dashboard({ onViewItems, onViewStreams }: DashboardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
    refetchInterval: 60_000,
  })

  if (isLoading) return <PageLoading />

  if (error || !data) {
    return (
      <div className="py-20 text-center">
        <p className="page-body text-muted">Unable to connect to Momentum Engine</p>
        <p className="page-meta mt-2 opacity-60">Start the backend: uvicorn app.main:app --reload</p>
      </div>
    )
  }

  const nextFocus = data.todays_focus[1] ?? null

  return (
    <>
      <FocusMode nextFocus={nextFocus} />
      <PageShell
        title="Today"
        wide
        actions={
          <>
            {onViewStreams && (
              <Button variant="ghost" size="md" onClick={onViewStreams} className="text-muted">
                <GitBranch className="mr-1.5 h-4 w-4 opacity-60" />
                Streams
              </Button>
            )}
            {onViewItems && (
              <Button variant="ghost" size="md" onClick={onViewItems} className="text-muted">
                <List className="mr-1.5 h-4 w-4 opacity-60" />
                Items
              </Button>
            )}
            <CaptureBox />
          </>
        }
      >
        <TodaysFocus focus={data.todays_focus} />
      </PageShell>
    </>
  )
}
