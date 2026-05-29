import type { Item } from '@/lib/api'

export const ITEM_STATUS_ORDER = ['next', 'active', 'backlog', 'completed', 'archived'] as const

const HIDDEN_FROM_QUEUE = new Set(['completed', 'archived'])

export function filterQueuedItems(items: Item[]): Item[] {
  return items.filter((item) => !HIDDEN_FROM_QUEUE.has(item.status))
}

export function sortQueuedItems(items: Item[]): Item[] {
  return [...items].sort((a, b) => {
    const statusDiff =
      ITEM_STATUS_ORDER.indexOf(a.status as (typeof ITEM_STATUS_ORDER)[number]) -
      ITEM_STATUS_ORDER.indexOf(b.status as (typeof ITEM_STATUS_ORDER)[number])
    if (statusDiff !== 0) return statusDiff
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  })
}

export function statusLabel(status: string): string {
  return status.replace('_', ' ')
}
