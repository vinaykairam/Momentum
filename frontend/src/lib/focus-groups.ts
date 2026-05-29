import type { FocusRecommendation } from '@/lib/api'

export interface FocusGroup {
  key: string
  parentName: string | null
  items: FocusRecommendation[]
  isGrouped: boolean
}

export function groupFocusRecommendations(focus: FocusRecommendation[]): FocusGroup[] {
  const groups: FocusGroup[] = []
  const parentIndex = new Map<string, number>()

  for (const item of focus) {
    if (item.parent_stream_name) {
      const parent = item.parent_stream_name
      let index = parentIndex.get(parent)
      if (index === undefined) {
        index = groups.length
        parentIndex.set(parent, index)
        groups.push({ key: parent, parentName: parent, items: [], isGrouped: true })
      }
      groups[index].items.push(item)
    } else {
      groups.push({
        key: `${item.stream_id}-${item.item_id ?? 'focus'}`,
        parentName: null,
        items: [item],
        isGrouped: false,
      })
    }
  }

  return groups
}
