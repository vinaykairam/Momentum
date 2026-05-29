import { Button } from '@/components/ui/button'
import type { FocusRecommendation } from '@/lib/api'
import { formatDuration, momentumStateColor } from '@/lib/utils'
import { useAppStore } from '@/store/app'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles } from 'lucide-react'

interface FocusCardProps {
  focus: FocusRecommendation
  index: number
  featured?: boolean
}

export function FocusCard({ focus, index, featured }: FocusCardProps) {
  const enterFocus = useAppStore((s) => s.enterFocus)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className={`glass group rounded-2xl p-6 ${featured ? 'ring-1 ring-accent/30 bg-accent-soft' : ''}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-widest text-muted">{focus.stream_name}</span>
        {focus.recovery_mode && (
          <span className="inline-flex items-center gap-1 rounded-full bg-critical/10 px-2 py-0.5 text-xs text-critical">
            <Sparkles className="h-3 w-3" />
            Recovery
          </span>
        )}
      </div>
      <h3 className={`mb-4 text-xl font-semibold tracking-tight ${featured ? 'text-2xl' : ''}`}>
        {focus.action}
      </h3>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm text-muted">
          {focus.estimated_minutes && <span>{formatDuration(focus.estimated_minutes)}</span>}
          <span className={momentumStateColor(focus.momentum_state)}>
            {focus.momentum_state}
          </span>
        </div>
        <Button
          variant={featured ? 'accent' : 'outline'}
          size="sm"
          onClick={() => enterFocus(focus)}
          className="gap-1 opacity-0 transition-opacity group-hover:opacity-100"
        >
          Focus
          <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </motion.div>
  )
}
