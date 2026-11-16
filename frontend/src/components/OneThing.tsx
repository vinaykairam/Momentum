import { Button } from '@/components/ui/button'
import { api, type FocusRecommendation } from '@/lib/api'
import { formatStreamLabel, isLabLessonTitle } from '@/lib/utils'
import { useAppStore } from '@/store/app'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Loader2, Play } from 'lucide-react'
import { useEffect } from 'react'

interface OneThingProps {
  focus: FocusRecommendation
}

const ease = [0.25, 0.1, 0.25, 1] as const

/** Today's single commitment, with the tiny step that gets it started. */
export function OneThing({ focus }: OneThingProps) {
  const queryClient = useQueryClient()
  const enterFocus = useAppStore((s) => s.enterFocus)
  const isLab = isLabLessonTitle(focus.action)
  const needsStep = focus.item_id !== null && !focus.first_step && !isLab

  // Items captured before first steps existed get one written the first time they reach the top.
  const { data: filled, isFetching } = useQuery({
    queryKey: ['first-step', focus.item_id],
    queryFn: () => api.ensureFirstStep(focus.item_id!),
    enabled: needsStep,
    staleTime: Infinity,
    retry: false,
  })
  useEffect(() => {
    if (filled?.first_step) queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }, [filled?.first_step, queryClient])

  const firstStep = focus.first_step ?? filled?.first_step ?? null
  const withStep: FocusRecommendation = { ...focus, first_step: firstStep }

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease }}
      className="stream-group px-5 md:px-6"
    >
      <p className="page-label">Your one thing today</p>
      <button
        type="button"
        onClick={() => enterFocus(withStep)}
        className="focus-item mt-3 block w-full text-left"
      >
        <span className="page-meta block">
          {formatStreamLabel(focus.stream_name, focus.parent_stream_name)}
        </span>
        <span className="page-body mt-1 block">{focus.action}</span>
      </button>

      {!isLab && (
        <div className="mt-5 border-t border-border pt-5">
          <p className="page-meta">First step · under 10 min</p>
          {firstStep ? (
            <p className="mt-1 text-lg leading-relaxed">{firstStep}</p>
          ) : isFetching ? (
            <p className="page-meta mt-1 inline-flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Finding the smallest way in…
            </p>
          ) : (
            <p className="mt-1 text-lg leading-relaxed">Just open it and do 10 minutes.</p>
          )}
        </div>
      )}

      <Button
        variant="accent"
        size="lg"
        className="mt-6 w-full gap-2"
        onClick={() => enterFocus(withStep, { startTimer: true })}
      >
        <Play className="h-4 w-4" />
        Start 10 minutes
      </Button>
      {focus.skip_count > 0 && (
        <p className="page-meta mt-3 text-center">
          Put off {focus.skip_count} {focus.skip_count === 1 ? 'time' : 'times'}
        </p>
      )}
    </motion.section>
  )
}
