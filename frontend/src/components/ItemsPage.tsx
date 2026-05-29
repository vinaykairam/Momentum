import { CaptureBox } from '@/components/CaptureBox'
import { ItemRow } from '@/components/ItemRow'
import { PageLoading, PageShell } from '@/components/PageShell'
import { Button } from '@/components/ui/button'
import { api, type Stream } from '@/lib/api'
import { filterQueuedItems, sortQueuedItems } from '@/lib/item-queue'
import { groupItemsByStreamTree, type StreamItemGroup } from '@/lib/stream-tree'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'

interface ItemsPageProps {
  onBack: () => void
}

const ease = [0.25, 0.1, 0.25, 1] as const

function StreamQueue({
  group,
  streams,
  nested,
  confirmDeleteId,
  isDeleting,
  onConfirmDelete,
  onCancelDelete,
  onDelete,
  onMoved,
}: {
  group: StreamItemGroup
  streams: Stream[]
  nested?: boolean
  confirmDeleteId: number | null
  isDeleting: boolean
  onConfirmDelete: (id: number) => void
  onCancelDelete: () => void
  onDelete: (id: number) => void
  onMoved: () => void
}) {
  const queuedItems = sortQueuedItems(group.items)
  const hasChildren = group.children.length > 0

  const renderItemRow = (item: (typeof queuedItems)[number], index: number) => {
    const prev = queuedItems[index - 1]
    const next = queuedItems[index + 1]
    return (
      <ItemRow
        key={item.id}
        item={item}
        streams={streams}
        queuePosition={index + 1}
        canMoveUp={index > 0 && prev.status === item.status}
        canMoveDown={index < queuedItems.length - 1 && next.status === item.status}
        confirmDeleteId={confirmDeleteId}
        isDeleting={isDeleting}
        onConfirmDelete={onConfirmDelete}
        onCancelDelete={onCancelDelete}
        onDelete={onDelete}
        onMoved={onMoved}
      />
    )
  }

  if (hasChildren) {
    return (
      <>
        {!nested && <p className="page-label pb-2 pt-5 first:pt-0">{group.stream.name}</p>}
        {queuedItems.length > 0 && (
          <div className="divide-y divide-border/40">
            {queuedItems.map(renderItemRow)}
          </div>
        )}
        {group.children.map((child) => (
          <div key={child.stream.id} className="ml-0 pt-2">
            <StreamQueue
              group={child}
              streams={streams}
              nested
              confirmDeleteId={confirmDeleteId}
              isDeleting={isDeleting}
              onConfirmDelete={onConfirmDelete}
              onCancelDelete={onCancelDelete}
              onDelete={onDelete}
              onMoved={onMoved}
            />
          </div>
        ))}
      </>
    )
  }

  return (
    <>
      <p className={`page-label ${nested ? 'pb-2 pt-4' : 'pb-2 pt-5 first:pt-0'}`}>{group.stream.name}</p>
      <div className="divide-y divide-border/40">
        {queuedItems.map(renderItemRow)}
      </div>
    </>
  )
}

export function ItemsPage({ onBack }: ItemsPageProps) {
  const queryClient = useQueryClient()
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const { data: items, isLoading, error } = useQuery({
    queryKey: ['items'],
    queryFn: api.getItems,
  })

  const { data: streams } = useQuery({
    queryKey: ['streams'],
    queryFn: api.getStreams,
  })

  const activeItems = useMemo(() => filterQueuedItems(items ?? []), [items])

  const groupedItems = useMemo(() => {
    if (!streams) return []
    return groupItemsByStreamTree(streams, activeItems)
  }, [activeItems, streams])

  const deleteMutation = useMutation({
    mutationFn: api.deleteItem,
    onSuccess: () => {
      setConfirmDeleteId(null)
      queryClient.invalidateQueries({ queryKey: ['items'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const invalidateAfterMove = () => {
    queryClient.invalidateQueries({ queryKey: ['items'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  if (isLoading) return <PageLoading />

  if (error || !items || !streams) {
    return (
      <div className="py-20 text-center">
        <p className="page-body text-muted">Unable to load items</p>
        <Button variant="ghost" size="md" className="mt-4" onClick={onBack}>
          Back
        </Button>
      </div>
    )
  }

  const rowHandlers = {
    streams,
    confirmDeleteId,
    isDeleting: deleteMutation.isPending,
    onConfirmDelete: setConfirmDeleteId,
    onCancelDelete: () => setConfirmDeleteId(null),
    onDelete: (id: number) => deleteMutation.mutate(id),
    onMoved: invalidateAfterMove,
  }

  return (
    <PageShell
      title="All Items"
      subtitle={`${activeItems.length} queued`}
      onBack={onBack}
      actions={<CaptureBox />}
    >
      {groupedItems.length === 0 ? (
        <p className="page-body py-16 text-center text-muted">No items yet. Use Capture to add something.</p>
      ) : (
        <div className="divide-y divide-border/40">
          {groupedItems.map((group, groupIndex) => (
            <motion.section
              key={group.stream.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: groupIndex * 0.04, duration: 0.5, ease }}
            >
              <StreamQueue group={group} {...rowHandlers} />
            </motion.section>
          ))}
        </div>
      )}
    </PageShell>
  )
}
