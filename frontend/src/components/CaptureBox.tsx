import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useAppStore } from '@/store/app'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2, Plus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

export function CaptureBox() {
  const open = useAppStore((s) => s.captureOpen)
  const setOpen = useAppStore((s) => s.setCaptureOpen)
  const [content, setContent] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (text: string) => api.capture(text),
    onSuccess: () => {
      setContent('')
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
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

  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)} className="gap-1.5 text-muted">
        <Plus className="h-4 w-4" />
        Capture
        <kbd className="ml-1 rounded bg-black/5 px-1.5 py-0.5 text-[10px] font-mono dark:bg-white/10">⌘J</kbd>
      </Button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center bg-black/20 p-4 pt-[15vh] backdrop-blur-sm"
            onClick={() => setOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -8 }}
              className="glass w-full max-w-xl rounded-2xl p-6 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold">Capture anything</h2>
                <button onClick={() => setOpen(false)} className="rounded-lg p-1 hover:bg-black/5 dark:hover:bg-white/5">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <textarea
                ref={inputRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste a task, idea, YouTube link, article, note..."
                rows={4}
                className="w-full resize-none rounded-xl border border-border bg-transparent p-4 text-base outline-none placeholder:text-muted/60 focus:ring-2 focus:ring-accent/30"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && content.trim()) {
                    mutation.mutate(content.trim())
                  }
                }}
              />
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-muted">AI will classify and assign to a stream</span>
                <Button
                  variant="accent"
                  disabled={!content.trim() || mutation.isPending}
                  onClick={() => mutation.mutate(content.trim())}
                >
                  {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Capture'}
                </Button>
              </div>
              {mutation.isSuccess && (
                <p className="mt-3 text-sm text-thriving">
                  Saved to {mutation.data.suggested_stream_name} ({Math.round(mutation.data.confidence * 100)}% confidence)
                </p>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
