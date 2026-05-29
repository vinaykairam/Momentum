import { Button } from '@/components/ui/button'
import { StreamSelect } from '@/components/StreamSelect'
import { StreamSuggestionPicker } from '@/components/StreamSuggestionPicker'
import { api, type StreamSuggestion } from '@/lib/api'
import { useAppStore } from '@/store/app'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, ChevronUp, Loader2, Plus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const ease = [0.25, 0.1, 0.25, 1] as const
const SUGGEST_DEBOUNCE_MS = 700
/** Min trimmed length before calling suggest-stream (single words like "rowing" are allowed). */
const MIN_SUGGEST_LENGTH = 3

export function CaptureBox() {
  const open = useAppStore((s) => s.captureOpen)
  const setOpen = useAppStore((s) => s.setCaptureOpen)
  const [content, setContent] = useState('')
  const [streamId, setStreamId] = useState<number | ''>('')
  const [suggestion, setSuggestion] = useState<StreamSuggestion | null>(null)
  const [suggesting, setSuggesting] = useState(false)
  const [showManualStream, setShowManualStream] = useState(false)
  const [userPickedStream, setUserPickedStream] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const suggestRequestId = useRef(0)
  const queryClient = useQueryClient()

  const { data: streams = [] } = useQuery({
    queryKey: ['streams'],
    queryFn: api.getStreams,
    enabled: open,
  })

  const mutation = useMutation({
    mutationFn: ({ text, stream }: { text: string; stream: number }) => api.capture(text, stream),
    onSuccess: () => {
      setContent('')
      setStreamId('')
      setSuggestion(null)
      setShowManualStream(false)
      setUserPickedStream(false)
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['items'] })
    },
  })

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'j') {
        e.preventDefault()
        setOpen(true)
      }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [setOpen])

  useEffect(() => {
    if (!open) return

    const trimmed = content.trim()
    if (trimmed.length < MIN_SUGGEST_LENGTH) {
      setSuggestion(null)
      setSuggesting(false)
      if (!userPickedStream) setStreamId('')
      return
    }

    const requestId = ++suggestRequestId.current
    setSuggesting(true)

    const timer = window.setTimeout(async () => {
      try {
        const result = await api.suggestStream(trimmed)
        if (requestId !== suggestRequestId.current) return

        setSuggestion(result)
        if (result.status === 'unavailable') {
          setShowManualStream(true)
        }
        if (!userPickedStream) {
          if (result.status === 'confident' && result.recommended) {
            setStreamId(result.recommended.stream_id)
          } else if (result.status === 'ambiguous') {
            setStreamId('')
          }
        }
      } catch {
        if (requestId !== suggestRequestId.current) return
        setSuggestion({
          status: 'unavailable',
          recommended: null,
          options: [],
          reasoning: 'Could not get a suggestion. Pick a stream below.',
        })
        setShowManualStream(true)
      } finally {
        if (requestId === suggestRequestId.current) {
          setSuggesting(false)
        }
      }
    }, SUGGEST_DEBOUNCE_MS)

    return () => window.clearTimeout(timer)
  }, [content, open, userPickedStream])

  const handleStreamSelect = (value: number | '') => {
    setUserPickedStream(true)
    setStreamId(value)
  }

  const handleSuggestionSelect = (id: number) => {
    setUserPickedStream(true)
    setStreamId(id)
  }

  const canCapture = content.trim().length > 0 && streamId !== ''

  const handleCapture = () => {
    if (!canCapture) return
    mutation.mutate({
      text: content.trim(),
      stream: streamId as number,
    })
  }

  const resetOnClose = () => {
    setOpen(false)
    setSuggestion(null)
    setShowManualStream(false)
    setUserPickedStream(false)
  }

  return (
    <>
      <Button variant="ghost" size="md" onClick={() => setOpen(true)} className="gap-1.5 text-muted">
        <Plus className="h-4 w-4 opacity-60" />
        Capture
        <kbd className="ml-1 rounded bg-black/5 px-1.5 py-0.5 text-xs font-mono dark:bg-white/10">⌘J</kbd>
      </Button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease }}
            className="fixed inset-0 z-50 flex items-start justify-center bg-black/20 p-4 pt-[10vh] backdrop-blur-sm"
            onClick={resetOnClose}
          >
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 12 }}
              transition={{ duration: 0.35, ease }}
              className="glass w-full max-w-2xl rounded-2xl p-6 md:p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-6 flex items-center justify-between">
                <h2 className="page-title text-2xl md:text-3xl">Capture</h2>
                <button
                  onClick={resetOnClose}
                  className="rounded-lg p-2 text-muted transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <textarea
                ref={inputRef}
                value={content}
                onChange={(e) => {
                  setContent(e.target.value)
                  setUserPickedStream(false)
                }}
                placeholder="Task, idea, link, note..."
                rows={4}
                className="field-input resize-none text-lg leading-relaxed"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && canCapture) {
                    handleCapture()
                  }
                }}
              />

              <div className="mt-5 space-y-3">
                <label className="page-label">Stream</label>
                <StreamSuggestionPicker
                  suggestion={suggestion}
                  isLoading={suggesting && content.trim().length >= MIN_SUGGEST_LENGTH}
                  waitingForMoreInput={
                    content.trim().length > 0 && content.trim().length < MIN_SUGGEST_LENGTH
                  }
                  selectedStreamId={streamId}
                  onSelect={handleSuggestionSelect}
                />

                <button
                  type="button"
                  onClick={() => setShowManualStream((v) => !v)}
                  className="page-meta flex items-center gap-1 text-accent hover:underline"
                >
                  {showManualStream ? (
                    <>
                      Hide stream list <ChevronUp className="h-3.5 w-3.5" />
                    </>
                  ) : (
                    <>
                      Choose stream manually <ChevronDown className="h-3.5 w-3.5" />
                    </>
                  )}
                </button>

                {showManualStream && (
                  <StreamSelect
                    streams={streams}
                    value={streamId}
                    onChange={handleStreamSelect}
                    disabled={mutation.isPending}
                  />
                )}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <span className="page-meta">⌘↵ to capture</span>
                <Button variant="accent" size="md" disabled={!canCapture || mutation.isPending} onClick={handleCapture}>
                  {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Capture'}
                </Button>
              </div>

              {mutation.isSuccess && (
                <p className="page-meta mt-4 text-thriving">Saved to {mutation.data.stream_name}</p>
              )}
              {mutation.isError && (
                <p className="page-meta mt-4 text-critical">
                  {mutation.error instanceof Error ? mutation.error.message : 'Could not capture.'}
                </p>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
