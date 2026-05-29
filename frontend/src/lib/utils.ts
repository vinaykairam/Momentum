import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(minutes: number | null | undefined): string {
  if (!minutes) return ''
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h}h ${m}m` : `${h}h`
}

export function momentumStateColor(state: string): string {
  switch (state) {
    case 'thriving':
      return 'text-thriving'
    case 'healthy':
      return 'text-healthy'
    case 'slowing':
      return 'text-slowing'
    case 'neglected':
      return 'text-neglected'
    case 'critical':
      return 'text-critical'
    default:
      return 'text-muted'
  }
}

export function momentumBarColor(state: string): string {
  switch (state) {
    case 'thriving':
      return 'bg-thriving'
    case 'healthy':
      return 'bg-healthy'
    case 'slowing':
      return 'bg-slowing'
    case 'neglected':
      return 'bg-neglected'
    case 'critical':
      return 'bg-critical'
    default:
      return 'bg-muted'
  }
}
