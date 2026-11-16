import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'

const ease = [0.25, 0.1, 0.25, 1] as const

interface PageShellProps {
  title: string
  subtitle?: string
  onBack?: () => void
  backLabel?: string
  actions?: ReactNode
  /** Use the full page width (e.g. side-by-side columns). */
  wide?: boolean
  children: ReactNode
}

export function PageLoading() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <motion.div
        animate={{ opacity: [0.3, 0.7, 0.3] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        className="h-1 w-8 rounded-full bg-foreground/20"
      />
    </div>
  )
}

export function PageShell({ title, subtitle, onBack, backLabel = 'Today', actions, wide, children }: PageShellProps) {
  return (
    <div className={`mx-auto ${wide ? 'max-w-7xl' : 'max-w-2xl'} px-6 py-12 md:py-16`}>
      <motion.header
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, ease }}
        className={`flex gap-6 ${onBack ? 'mb-12 flex-col' : 'mb-14 items-center justify-between'}`}
      >
        <div className={onBack ? undefined : 'min-w-0'}>
          {onBack && (
            <Button
              variant="ghost"
              size="md"
              onClick={onBack}
              className="-ml-2 mb-4 gap-1.5 text-base font-normal text-muted"
            >
              <ArrowLeft className="h-4 w-4 opacity-60" />
              {backLabel}
            </Button>
          )}
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle mt-2">{subtitle}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-1">{actions}</div>}
      </motion.header>
      {children}
    </div>
  )
}
