import type { Stream } from '@/lib/api'
import { getStreamPath } from '@/lib/utils'
import { buildStreamTree } from '@/lib/stream-tree'

export interface StreamOption {
  id: number
  label: string
  depth: number
}

export function buildStreamOptions(streams: Stream[]): StreamOption[] {
  const options: StreamOption[] = []

  for (const node of buildStreamTree(streams)) {
    options.push({ id: node.stream.id, label: node.stream.name, depth: 0 })
    for (const child of node.children) {
      options.push({
        id: child.stream.id,
        label: getStreamPath(child.stream.id, streams),
        depth: 1,
      })
    }
  }

  return options
}
