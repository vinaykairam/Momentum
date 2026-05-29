import { cn, momentumBarColor } from '@/lib/utils'
import { motion } from 'framer-motion'

interface MomentumBarProps {
  score: number
  state: string
  name: string
  nested?: boolean
}

export function MomentumBar({ score, state, name, nested }: MomentumBarProps) {
  return (
    <div className={cn('space-y-2', nested && 'opacity-90')}>
      <div className="flex items-baseline justify-between gap-4">
        <span className={cn('font-medium', nested ? 'text-xs text-muted' : 'text-sm')}>{name}</span>
        <span className="tabular-nums text-sm text-muted">{Math.round(score)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-black/5 dark:bg-white/5">
        <motion.div
          className={`h-full rounded-full ${momentumBarColor(state)}`}
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  )
}
