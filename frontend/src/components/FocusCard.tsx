import type { FocusRecommendation } from '@/lib/api'
import { formatStreamLabel } from '@/lib/utils'
import { useAppStore } from '@/store/app'
import { motion } from 'framer-motion'

interface FocusCardProps {
  focus: FocusRecommendation
  index: number
  nested?: boolean
}

const ease = [0.25, 0.1, 0.25, 1] as const

export function FocusCard({ focus, index, nested }: FocusCardProps) {
  const enterFocus = useAppStore((s) => s.enterFocus)

  const streamLabel = nested ? focus.stream_name : formatStreamLabel(focus.stream_name, focus.parent_stream_name)

  return (
    <motion.button
      type="button"
      onClick={() => enterFocus(focus)}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.04, duration: 0.5, ease }}
      className={`focus-item group w-full text-left ${nested ? 'py-4 md:py-5' : 'py-1 md:py-2'}`}
    >
      <span className="page-label block transition-colors group-hover:text-foreground/70">{streamLabel}</span>
      <span className="page-body mt-1.5 block">{focus.action}</span>
    </motion.button>
  )
}
