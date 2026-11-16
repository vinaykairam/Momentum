import { FocusTimer } from '@/components/FocusTimer'
import { Button } from '@/components/ui/button'
import { api, type Item } from '@/lib/api'
import { formatStreamLabel, isLabLessonTitle } from '@/lib/utils'
import { useAppStore } from '@/store/app'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Archive, ChevronLeft, ChevronRight, ExternalLink, Loader2, Moon, Scissors, TrendingUp, X } from 'lucide-react'
import { useEffect, useState } from 'react'

interface FocusModeProps {
  nextFocus?: import('@/lib/api').FocusRecommendation | null
}

const ease = [0.25, 0.1, 0.25, 1] as const

export function FocusMode({ nextFocus }: FocusModeProps) {
  const queryClient = useQueryClient()
  const focusMode = useAppStore((s) => s.focusMode)
  const activeFocus = useAppStore((s) => s.activeFocus)
  const exitFocus = useAppStore((s) => s.exitFocus)
  const autoStartTimer = useAppStore((s) => s.autoStartTimer)

  const itemId = activeFocus?.item_id ?? null
  const [notes, setNotes] = useState('')
  const [confirmDrop, setConfirmDrop] = useState(false)
  const [splitSteps, setSplitSteps] = useState<Item[] | null>(null)
  useEffect(() => {
    setConfirmDrop(false)
    setSplitSteps(null)
  }, [itemId])
  // Lab lessons: which lesson is on screen (browsing back through earlier lessons).
  const [viewId, setViewId] = useState<number | null>(itemId)
  useEffect(() => setViewId(itemId), [itemId])
  const viewingCurrent = viewId === itemId

  const { data: currentItem, isLoading: itemLoading } = useQuery({
    queryKey: ['item', itemId],
    queryFn: () => api.getItem(itemId!),
    enabled: focusMode && itemId !== null,
  })
  const { data: viewedItem, isLoading: viewedLoading } = useQuery({
    queryKey: ['item', viewId],
    queryFn: () => api.getItem(viewId!),
    enabled: focusMode && viewId !== null && !viewingCurrent,
  })
  const item = viewingCurrent ? currentItem : viewedItem
  const isLabLesson = isLabLessonTitle(item?.title)
  const { data: neighbors } = useQuery({
    queryKey: ['lab-neighbors', viewId],
    queryFn: () => api.getLabNeighbors(viewId!),
    enabled: focusMode && viewId !== null && isLabLesson,
  })

  useEffect(() => {
    const item = currentItem
    if (item) {
      setNotes(item.notes ?? '')
    } else {
      setNotes('')
    }
  }, [currentItem?.id, currentItem?.notes])

  const refreshQueues = () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    queryClient.invalidateQueries({ queryKey: ['items'] })
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }
  const trimmedNotes = () => notes.trim() || null

  const progressMutation = useMutation({
    mutationFn: () => api.logProgress(itemId!, trimmedNotes()),
    onSuccess: () => {
      refreshQueues()
      exitFocus()
    },
  })
  const snoozeMutation = useMutation({
    mutationFn: (days: number) => api.snoozeItem(itemId!, days, trimmedNotes()),
    onSuccess: () => {
      refreshQueues()
      exitFocus()
    },
  })
  const dropMutation = useMutation({
    mutationFn: () => api.updateItem(itemId!, { status: 'archived', notes: trimmedNotes() }),
    onSuccess: () => {
      refreshQueues()
      exitFocus()
    },
  })
  const splitMutation = useMutation({
    mutationFn: async () => {
      if (notes.trim() !== (currentItem?.notes ?? '').trim()) {
        await api.updateItem(itemId!, { notes: trimmedNotes() })
      }
      return api.splitItem(itemId!)
    },
    onSuccess: (steps) => {
      refreshQueues()
      setSplitSteps(steps)
    },
  })
  const busy =
    progressMutation.isPending || snoozeMutation.isPending || dropMutation.isPending || splitMutation.isPending
  const actionError = [progressMutation, snoozeMutation, dropMutation, splitMutation].find((m) => m.isError)?.error

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
  const canLogDone = Boolean(
    viewingCurrent && itemId !== null && item && item.status !== 'completed' && item.status !== 'archived',
  )
  const currentIsLab = isLabLessonTitle(currentItem?.title ?? activeFocus.action)
  const firstStep = currentItem?.first_step ?? activeFocus.first_step
  const skipCount = currentItem?.skip_count ?? activeFocus.skip_count ?? 0

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.35, ease }}
        className="fixed inset-0 z-[100] flex flex-col bg-background"
      >
        <div className="flex justify-end p-6 md:p-8">
          <Button variant="ghost" size="md" onClick={exitFocus} className="gap-1.5 text-muted">
            <X className="h-4 w-4" />
            Close
          </Button>
        </div>

        <div className="flex flex-1 flex-col items-center overflow-y-auto px-6 pb-10 md:px-8">
          <div className="w-full max-w-2xl pt-4 md:pt-8">
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.05, duration: 0.4, ease }}
              className="page-label"
            >
              {streamLabel}
            </motion.p>

            <motion.h1
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.45, ease }}
              className="page-body mt-3 md:mt-4"
            >
              {displayTitle}
            </motion.h1>

            {isLabLesson && (neighbors?.previous || neighbors?.next || !viewingCurrent) && (
              <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2">
                {neighbors?.previous && (
                  <button
                    type="button"
                    onClick={() => setViewId(neighbors.previous!.id)}
                    className="page-meta inline-flex items-center gap-1 hover:text-foreground"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous: {neighbors.previous.title}
                  </button>
                )}
                {!viewingCurrent && neighbors?.next && (
                  <button
                    type="button"
                    onClick={() => setViewId(neighbors.next!.id)}
                    className="page-meta inline-flex items-center gap-1 hover:text-foreground"
                  >
                    Next: {neighbors.next.title}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                )}
                {!viewingCurrent && (
                  <button
                    type="button"
                    onClick={() => setViewId(itemId)}
                    className="page-meta font-medium text-foreground underline underline-offset-4"
                  >
                    Back to current lesson
                  </button>
                )}
              </div>
            )}

            {canLogDone && !splitSteps && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.12, duration: 0.4, ease }}
                className="mt-8 rounded-2xl border border-border p-5"
              >
                {firstStep && !currentIsLab && (
                  <>
                    <p className="page-meta">First step</p>
                    <p className="mt-1 mb-4 text-lg leading-relaxed">{firstStep}</p>
                  </>
                )}
                <FocusTimer key={itemId} autoStart={autoStartTimer} />
              </motion.div>
            )}

            {canLogDone && !splitSteps && !currentIsLab && skipCount >= 3 && (
              <div className="mt-4 rounded-2xl bg-accent-soft p-5">
                <p className="text-lg">You've put this off {skipCount} times.</p>
                <p className="page-meta mt-1">
                  That usually means it's too big or doesn't matter anymore. Shrink it or drop it?
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" disabled={busy} onClick={() => splitMutation.mutate()} className="gap-1.5">
                    <Scissors className="h-4 w-4" /> Break it down
                  </Button>
                  <Button variant="outline" size="sm" disabled={busy} onClick={() => dropMutation.mutate()} className="gap-1.5">
                    <Archive className="h-4 w-4" /> Drop it
                  </Button>
                </div>
              </div>
            )}

            {splitSteps && (
              <div className="mt-8 rounded-2xl border border-border p-5">
                <p className="page-meta">Broken into {splitSteps.length} steps, in your queue now:</p>
                <ol className="mt-3 list-decimal space-y-2 pl-6 text-lg">
                  {splitSteps.map((step) => (
                    <li key={step.id}>{step.title}</li>
                  ))}
                </ol>
                <Button variant="accent" size="lg" className="mt-6 w-full" onClick={exitFocus}>
                  Back to Today
                </Button>
              </div>
            )}

            {splitSteps ? null : itemId && (itemLoading || (!viewingCurrent && viewedLoading)) ? (
              <div className="mt-10 flex justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-muted" />
              </div>
            ) : (
              <>
                {item?.description && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.15, duration: 0.4, ease }}
                    className="page-meta mt-6 leading-relaxed whitespace-pre-line text-left"
                  >
                    {item.description}
                  </motion.p>
                )}

                {item?.url && (
                  <motion.a
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="page-meta mt-4 inline-flex items-center gap-1.5 hover:text-foreground"
                  >
                    Open link
                    <ExternalLink className="h-4 w-4" />
                  </motion.a>
                )}

                {viewingCurrent && itemId && item && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2, duration: 0.4, ease }}
                    className="mt-10 space-y-3"
                  >
                    <label htmlFor="focus-notes" className="page-label">
                      Notes
                    </label>
                    <textarea
                      id="focus-notes"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="What did you do? Follow-ups, thoughts..."
                      rows={4}
                      disabled={item.status === 'completed'}
                      className="field-input resize-none leading-relaxed disabled:opacity-60"
                    />
                  </motion.div>
                )}

                {canLogDone && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.25, duration: 0.4, ease }}
                    className="mt-8"
                  >
                    <Button
                      variant="accent"
                      size="lg"
                      className="w-full"
                      disabled={completeMutation.isPending}
                      onClick={() => completeMutation.mutate()}
                    >
                      {completeMutation.isPending ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        'Log done'
                      )}
                    </Button>

                    <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                      <Button
                        variant="outline"
                        size="md"
                        disabled={busy}
                        onClick={() => progressMutation.mutate()}
                        className="gap-1.5"
                        title="Made progress but not finished. Back tomorrow."
                      >
                        {progressMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />}
                        Worked on it
                      </Button>
                      <Button
                        variant="outline"
                        size="md"
                        disabled={busy}
                        onClick={() => snoozeMutation.mutate(1)}
                        className="gap-1.5"
                        title="Not today. Back tomorrow."
                      >
                        {snoozeMutation.isPending && snoozeMutation.variables === 1 ? <Loader2 className="h-4 w-4 animate-spin" /> : <Moon className="h-4 w-4" />}
                        Tomorrow
                      </Button>
                      <Button
                        variant="outline"
                        size="md"
                        disabled={busy}
                        onClick={() => snoozeMutation.mutate(7)}
                        className="gap-1.5"
                        title="Not this week. Back in 7 days."
                      >
                        {snoozeMutation.isPending && snoozeMutation.variables === 7 ? <Loader2 className="h-4 w-4 animate-spin" /> : <Moon className="h-4 w-4" />}
                        Next week
                      </Button>
                      {!currentIsLab && (
                        <Button
                          variant="outline"
                          size="md"
                          disabled={busy}
                          onClick={() => splitMutation.mutate()}
                          className="gap-1.5"
                          title="Break it into smaller steps"
                        >
                          {splitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scissors className="h-4 w-4" />}
                          Too big
                        </Button>
                      )}
                    </div>

                    {!currentIsLab && (
                      <div className="mt-4 text-center">
                        {confirmDrop ? (
                          <span className="page-meta inline-flex flex-wrap items-center justify-center gap-3">
                            Drop this for good? It moves to archived.
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => dropMutation.mutate()}
                              className="font-medium text-critical underline underline-offset-4"
                            >
                              Drop it
                            </button>
                            <button type="button" onClick={() => setConfirmDrop(false)} className="underline underline-offset-4">
                              Keep
                            </button>
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmDrop(true)}
                            className="page-meta inline-flex items-center gap-1.5 hover:text-foreground"
                          >
                            <Archive className="h-4 w-4" /> Don't want to do this anymore
                          </button>
                        )}
                      </div>
                    )}

                    {actionError && (
                      <p className="page-meta mt-3 text-center text-critical">
                        {actionError instanceof Error ? actionError.message : 'Something went wrong'}
                      </p>
                    )}
                    {completeMutation.isError && (
                      <p className="page-meta mt-3 text-center text-critical">
                        {completeMutation.error instanceof Error
                          ? completeMutation.error.message
                          : 'Could not log completion'}
                      </p>
                    )}
                  </motion.div>
                )}

                {item?.status === 'completed' && (
                  <div className="mt-8 space-y-3">
                    <p className="page-meta text-thriving">Logged as done</p>
                    {item.notes && <p className="page-meta leading-relaxed">{item.notes}</p>}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {nextFocus && nextFocus.item_id !== activeFocus.item_id && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.4, ease }}
            className="border-t border-border/40 px-6 py-5 text-center md:px-8"
          >
            <p className="page-meta">Up next</p>
            <p className="page-body mt-1 text-lg md:text-xl">
              {formatStreamLabel(nextFocus.stream_name, nextFocus.parent_stream_name)} · {nextFocus.action}
            </p>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
