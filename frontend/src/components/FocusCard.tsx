import type { FocusRecommendation } from '@/lib/api'
import { formatStreamLabel } from '@/lib/utils'
import { useAppStore } from '@/store/app'
import { motion } from 'framer-motion'

interface FocusCardProps {
  focus: FocusRecommendation
  index: number
  featured?: boolean
  nested?: boolean
}

const ease = [0.22, 1, 0.36, 1] as const

export function FocusCard({ focus, index, featured, nested }: FocusCardProps) {
  const enterFocus = useAppStore((s) => s.enterFocus)

  const streamLabel = nested ? focus.stream_name : formatStreamLabel(focus.stream_name, focus.parent_stream_name)

  const content = (
    <>
      <p className="mb-1.5 text-sm text-muted">{streamLabel}</p>
      <h3 className="text-xl font-medium leading-snug tracking-tight md:text-2xl">{focus.action}</h3>
    </>
  )

  if (nested) {
    return (
      <motion.button
        type="button"
        onClick={() => enterFocus(focus)}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05, duration: 0.4, ease }}
        whileTap={{ scale: 0.995 }}
        className="w-full rounded-xl py-4 text-left transition-colors hover:bg-black/[0.03] dark:hover:bg-white/[0.03]"
      >
        {content}
      </motion.button>
    )
  }

  return (
    <motion.button
      type="button"
      onClick={() => enterFocus(focus)}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.45, ease }}
      whileHover={{ y: -1, transition: { duration: 0.2, ease } }}
      whileTap={{ scale: 0.995 }}
      className={`glass w-full rounded-2xl p-6 text-left md:p-7 ${
        featured ? 'ring-1 ring-accent/20 bg-accent-soft' : ''
      }`}
    >
      {content}
    </motion.button>
  )
}
