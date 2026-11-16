import type { FocusRecommendation } from '@/lib/api'

export interface FocusGroup {
  key: string
  parentName: string | null
  items: FocusRecommendation[]
  isGrouped: boolean
}

/** Groups recommendations by top-level stream, so e.g. "Learn" and "Learn > Lab" share one group. */
export function groupFocusRecommendations(focus: FocusRecommendation[]): FocusGroup[] {
  const groups: FocusGroup[] = []
  const byName = new Map<string, FocusGroup>()

  for (const item of focus) {
    const topLevel = item.parent_stream_name ?? item.stream_name
    let group = byName.get(topLevel)
    if (!group) {
      group = { key: topLevel, parentName: topLevel, items: [], isGrouped: false }
      byName.set(topLevel, group)
      groups.push(group)
    }
    group.items.push(item)
  }

  for (const group of groups) {
    group.isGrouped = group.items.length > 1 || group.items.some((item) => item.parent_stream_name)
    if (!group.isGrouped) group.parentName = null
  }

  return groups
}
