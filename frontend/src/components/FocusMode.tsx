import { Button } from '@/components/ui/button'
import type { FocusRecommendation } from '@/lib/api'
import { formatDuration } from '@/lib/utils'
import { useAppStore } from '@/store/app'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useEffect } from 'react'

interface FocusModeProps {
  nextFocus?: FocusRecommendation | null
}

export function FocusMode({ nextFocus }: FocusModeProps) {
  const focusMode = useAppStore((s) => s.focusMode)
  const activeFocus = useAppStore((s) => s.activeFocus)
  const exitFocus = useAppStore((s) => s.exitFocus)

  useEffect(() => {
    if (!focusMode) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') exitFocus()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [focusMode, exitFocus])

  return (
    <AnimatePresence>
      {focusMode && activeFocus && (
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

          <div className="flex flex-1 flex-col items-center justify-center px-6 pb-24 text-center">
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-accent"
            >
              {activeFocus.stream_name}
            </motion.p>
            <motion.h1
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.5 }}
              className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight md:text-5xl"
            >
              {activeFocus.action}
            </motion.h1>
            {activeFocus.estimated_minutes && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="mt-6 text-lg text-muted"
              >
                {formatDuration(activeFocus.estimated_minutes)}
              </motion.p>
            )}
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
                <span className="text-muted">{nextFocus.stream_name}</span>
                {' · '}
                {nextFocus.action}
              </p>
            </motion.div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
