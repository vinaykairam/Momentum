import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { formatDuration, formatStreamLabel, momentumStateColor } from '@/lib/utils'
import { useAppStore } from '@/store/app'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, ExternalLink, Loader2, Sparkles, X } from 'lucide-react'
import { useEffect, useState } from 'react'

interface FocusModeProps {
  nextFocus?: import('@/lib/api').FocusRecommendation | null
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-muted">{label}</span>
      <span className="font-medium capitalize">{value}</span>
    </div>
  )
}

export function FocusMode({ nextFocus }: FocusModeProps) {
  const queryClient = useQueryClient()
  const focusMode = useAppStore((s) => s.focusMode)
  const activeFocus = useAppStore((s) => s.activeFocus)
  const exitFocus = useAppStore((s) => s.exitFocus)

  const itemId = activeFocus?.item_id ?? null
  const [notes, setNotes] = useState('')

  const { data: item, isLoading: itemLoading } = useQuery({
    queryKey: ['item', itemId],
    queryFn: () => api.getItem(itemId!),
    enabled: focusMode && itemId !== null,
  })

  useEffect(() => {
    if (item) {
      setNotes(item.notes ?? '')
    } else {
      setNotes('')
    }
  }, [item?.id, item?.notes])

  const completeMutation = useMutation({
    mutationFn: () =>
      api.updateItem(itemId!, {
        status: 'completed',
        notes: notes.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['items'] })
      queryClient.invalidateQueries({ queryKey: ['item', itemId] })
      exitFocus()
    },
  })

  useEffect(() => {
    if (!focusMode) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') exitFocus()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [focusMode, exitFocus])

  if (!focusMode || !activeFocus) return null

  const streamLabel = formatStreamLabel(activeFocus.stream_name, activeFocus.parent_stream_name)
  const displayTitle = item?.title ?? activeFocus.action
  const canLogDone = itemId !== null && item && item.status !== 'completed'

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex flex-col bg-background"
      >
        <div className="flex justify-end p-6">
          <Button variant="ghost" size="sm" onClick={exitFocus} className="gap-1.5 text-muted">
            <X className="h-4 w-4" />
            Exit Focus
          </Button>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-6 pb-8">
          <div className="w-full max-w-xl">
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="mb-6 flex flex-wrap items-center justify-center gap-2"
            >
              <span className="text-sm font-medium uppercase tracking-[0.2em] text-accent">
                {streamLabel}
              </span>
              {activeFocus.recovery_mode && (
                <span className="inline-flex items-center gap-1 rounded-full bg-critical/10 px-2 py-0.5 text-xs text-critical">
                  <Sparkles className="h-3 w-3" />
                  Recovery
                </span>
              )}
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.5 }}
              className="mb-8 text-center text-4xl font-semibold leading-tight tracking-tight md:text-5xl"
            >
              {displayTitle}
            </motion.h1>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="glass rounded-2xl p-6"
            >
              <h2 className="mb-4 text-xs font-medium uppercase tracking-widest text-muted">Details</h2>

              {itemId && itemLoading ? (
                <div className="flex justify-center py-6">
                  <Loader2 className="h-6 w-6 animate-spin text-muted" />
                </div>
              ) : item ? (
                <div className="space-y-3">
                  <DetailRow label="Type" value={item.item_type.replace('_', ' ')} />
                  <DetailRow label="Status" value={item.status} />
                  <DetailRow label="Importance" value={item.importance} />
                  <DetailRow label="Effort" value={item.effort_estimate} />
                  {(item.estimated_duration ?? activeFocus.estimated_minutes) && (
                    <DetailRow
                      label="Duration"
                      value={formatDuration(item.estimated_duration ?? activeFocus.estimated_minutes!)}
                    />
                  )}
                  <div className="flex items-center justify-between gap-4 text-sm">
                    <span className="text-muted">Stream momentum</span>
                    <span className={momentumStateColor(activeFocus.momentum_state)}>
                      {Math.round(activeFocus.momentum_score)} · {activeFocus.momentum_state}
                    </span>
                  </div>
                  {item.description && (
                    <p className="border-t border-border pt-3 text-sm leading-relaxed text-muted">
                      {item.description}
                    </p>
                  )}
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
                    >
                      Open link
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              ) : (
                <div className="space-y-3 text-sm text-muted">
                  {activeFocus.estimated_minutes && (
                    <DetailRow
                      label="Duration"
                      value={formatDuration(activeFocus.estimated_minutes)}
                    />
                  )}
                  <div className="flex items-center justify-between gap-4">
                    <span>Stream momentum</span>
                    <span className={momentumStateColor(activeFocus.momentum_state)}>
                      {Math.round(activeFocus.momentum_score)} · {activeFocus.momentum_state}
                    </span>
                  </div>
                  <p className="border-t border-border pt-3">
                    No linked item — this is a stream-level focus suggestion.
                  </p>
                </div>
              )}
            </motion.div>

            {itemId && item && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="mt-6 space-y-2"
              >
                <label htmlFor="focus-notes" className="text-xs font-medium uppercase tracking-widest text-muted">
                  Notes
                </label>
                <textarea
                  id="focus-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="What did you do? Any follow-ups, reps, links, or thoughts..."
                  rows={4}
                  disabled={item.status === 'completed'}
                  className="w-full resize-none rounded-xl border border-border bg-transparent p-4 text-sm leading-relaxed outline-none placeholder:text-muted/60 focus:ring-2 focus:ring-accent/30 disabled:opacity-60"
                />
              </motion.div>
            )}

            {canLogDone && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="mt-6"
              >
                <Button
                  variant="accent"
                  size="lg"
                  className="w-full gap-2"
                  disabled={completeMutation.isPending}
                  onClick={() => completeMutation.mutate()}
                >
                  {completeMutation.isPending ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-5 w-5" />
                  )}
                  Log done
                </Button>
                {completeMutation.isError && (
                  <p className="mt-2 text-center text-sm text-critical">
                    {completeMutation.error instanceof Error
                      ? completeMutation.error.message
                      : 'Could not log completion'}
                  </p>
                )}
              </motion.div>
            )}

            {item?.status === 'completed' && (
              <div className="mt-6 space-y-2 text-center">
                <p className="text-sm text-thriving">Logged as done</p>
                {item.notes && (
                  <p className="rounded-xl border border-border bg-black/[0.02] px-4 py-3 text-left text-sm leading-relaxed text-muted dark:bg-white/[0.02]">
                    {item.notes}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {nextFocus && nextFocus.item_id !== activeFocus.item_id && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="border-t border-border p-6 text-center"
          >
            <p className="mb-1 text-xs uppercase tracking-widest text-muted">Up next</p>
            <p className="text-sm">
              <span className="text-muted">
                {formatStreamLabel(nextFocus.stream_name, nextFocus.parent_stream_name)}
              </span>
              {' · '}
              {nextFocus.action}
            </p>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
