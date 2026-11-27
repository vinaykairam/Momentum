import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatStreamLabel(
  streamName: string,
  parentStreamName?: string | null,
): string {
  return parentStreamName ? `${parentStreamName} · ${streamName}` : streamName
}

export function getStreamPath(streamId: number, streams: { id: number; name: string; parent_id?: number | null }[]): string {
  const stream = streams.find((entry) => entry.id === streamId)
  if (!stream) return `Stream ${streamId}`
  if (stream.parent_id) {
    const parent = streams.find((entry) => entry.id === stream.parent_id)
    return parent ? formatStreamLabel(stream.name, parent.name) : stream.name
  }
  return stream.name
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

/** Lab lessons are written by the app; they skip first steps, splitting and dropping. */
export function isLabLessonTitle(title: string | null | undefined): boolean {
  return /^(Lesson|Math|Physics) \d+:/.test(title ?? '')
}
