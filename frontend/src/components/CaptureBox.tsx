import { Button } from '@/components/ui/button'
import { StreamSelect } from '@/components/StreamSelect'
import { api } from '@/lib/api'
import { useAppStore } from '@/store/app'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2, Plus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const ease = [0.25, 0.1, 0.25, 1] as const

export function CaptureBox() {
  const open = useAppStore((s) => s.captureOpen)
  const setOpen = useAppStore((s) => s.setCaptureOpen)
  const [content, setContent] = useState('')
  const [streamId, setStreamId] = useState<number | ''>('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
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

  const canCapture = content.trim().length > 0 && streamId !== ''

  const handleCapture = () => {
    if (!canCapture) return
    mutation.mutate({
      text: content.trim(),
      stream: streamId as number,
    })
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
            onClick={() => setOpen(false)}
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
                  onClick={() => setOpen(false)}
                  className="rounded-lg p-2 text-muted transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <textarea
                ref={inputRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Task, idea, link, note..."
                rows={4}
                className="field-input resize-none text-lg leading-relaxed"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && canCapture) {
                    handleCapture()
                  }
                }}
              />

              <div className="mt-5 space-y-2">
                <label className="page-label">Stream</label>
                <StreamSelect
                  streams={streams}
                  value={streamId}
                  onChange={setStreamId}
                  disabled={mutation.isPending}
                />
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
