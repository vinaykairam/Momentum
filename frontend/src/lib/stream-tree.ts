import type { Stream } from '@/lib/api'

export interface StreamNode {
  stream: Stream
  children: StreamNode[]
}

export function buildStreamTree(streams: Stream[]): StreamNode[] {
  const roots = streams.filter((stream) => !stream.parent_id)

  return roots.map((stream) => ({
    stream,
    children: streams
      .filter((entry) => entry.parent_id === stream.id)
      .map((child) => ({ stream: child, children: [] })),
  }))
}

export interface StreamItemGroup {
  stream: Stream
  items: import('@/lib/api').Item[]
  children: StreamItemGroup[]
}

export function groupItemsByStreamTree(
  streams: Stream[],
  items: import('@/lib/api').Item[],
): StreamItemGroup[] {
  const itemsByStream = new Map<number, import('@/lib/api').Item[]>()
  for (const item of items) {
    const list = itemsByStream.get(item.stream_id) ?? []
    list.push(item)
    itemsByStream.set(item.stream_id, list)
  }

  const mapNode = (node: StreamNode): StreamItemGroup | null => {
    const ownItems = itemsByStream.get(node.stream.id) ?? []
    const children = node.children
      .map(mapNode)
      .filter((group): group is StreamItemGroup => group !== null)

    if (ownItems.length === 0 && children.length === 0) {
      return null
    }

    return {
      stream: node.stream,
      items: ownItems,
      children,
    }
  }

  return buildStreamTree(streams)
    .map(mapNode)
    .filter((group): group is StreamItemGroup => group !== null)
}
