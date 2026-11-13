import { CaptureBox } from '@/components/CaptureBox'
import { ItemRow } from '@/components/ItemRow'
import { PageLoading, PageShell } from '@/components/PageShell'
import { Button } from '@/components/ui/button'
import { api, ITEMS_CSV_URL, type Stream } from '@/lib/api'
import { filterQueuedItems, sortQueuedItems } from '@/lib/item-queue'
import { groupItemsByStreamTree, type StreamItemGroup } from '@/lib/stream-tree'
import { cn } from '@/lib/utils'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, Download } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'

interface ItemsPageProps {
  onBack: () => void
}

const ease = [0.25, 0.1, 0.25, 1] as const

function countGroupItems(group: StreamItemGroup): number {
  return group.items.length + group.children.reduce((sum, child) => sum + countGroupItems(child), 0)
}

function CollapsibleSection({
  title,
  itemCount,
  nested,
  children,
}: {
  title: string
  itemCount: number
  nested?: boolean
  children: ReactNode
}) {
  const [expanded, setExpanded] = useState(true)
  const panelId = `stream-panel-${title.replace(/\s+/g, '-').toLowerCase()}`

  return (
    <div className={cn(nested && 'border-l border-border/50 pl-4')}>
      <button
        type="button"
        className={cn(
          'flex w-full items-center gap-3 text-left transition-colors hover:text-foreground',
          nested ? 'py-3' : 'px-1 py-4',
        )}
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={() => setExpanded((open) => !open)}
      >
        <ChevronDown
          className={cn(
            'h-4 w-4 shrink-0 text-muted transition-transform duration-200',
            !expanded && '-rotate-90',
          )}
          aria-hidden="true"
        />
        <span className={cn('min-w-0 flex-1 truncate', nested ? 'page-label text-foreground' : 'page-body')}>
          {title}
        </span>
        <span className="page-meta shrink-0 tabular-nums">
          {itemCount} {itemCount === 1 ? 'item' : 'items'}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={panelId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease }}
            className="overflow-hidden"
          >
            <div className={cn(nested ? 'pb-1' : 'border-t border-border/40 px-1 pb-2 pt-1')}>{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

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
  editingItemId,
  onEdit,
  onCancelEdit,
  onSaved,
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
  editingItemId: number | null
  onEdit: (id: number) => void
  onCancelEdit: () => void
  onSaved: () => void
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
        editingItemId={editingItemId}
        onEdit={onEdit}
        onCancelEdit={onCancelEdit}
        onSaved={onSaved}
      />
    )
  }

  const itemCount = countGroupItems(group)

  const itemList =
    queuedItems.length > 0 ? (
      <div className="divide-y divide-border/40">{queuedItems.map(renderItemRow)}</div>
    ) : null

  if (hasChildren) {
    return (
      <CollapsibleSection title={group.stream.name} itemCount={itemCount} nested={nested}>
        {itemList}
        {group.children.length > 0 && (
          <div className={cn('space-y-1', itemList && 'mt-2')}>
            {group.children.map((child) => (
              <StreamQueue
                key={child.stream.id}
                group={child}
                streams={streams}
                nested
                confirmDeleteId={confirmDeleteId}
                isDeleting={isDeleting}
                onConfirmDelete={onConfirmDelete}
                onCancelDelete={onCancelDelete}
                onDelete={onDelete}
                onMoved={onMoved}
                editingItemId={editingItemId}
                onEdit={onEdit}
                onCancelEdit={onCancelEdit}
                onSaved={onSaved}
              />
            ))}
          </div>
        )}
      </CollapsibleSection>
    )
  }

  return (
    <CollapsibleSection title={group.stream.name} itemCount={itemCount} nested={nested}>
      {itemList}
    </CollapsibleSection>
  )
}

export function ItemsPage({ onBack }: ItemsPageProps) {
  const queryClient = useQueryClient()
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  const [editingItemId, setEditingItemId] = useState<number | null>(null)

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

  const invalidateItems = () => {
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
    onConfirmDelete: (id: number) => {
      setEditingItemId(null)
      setConfirmDeleteId(id)
    },
    onCancelDelete: () => setConfirmDeleteId(null),
    onDelete: (id: number) => deleteMutation.mutate(id),
    onMoved: invalidateItems,
    editingItemId,
    onEdit: (id: number) => {
      setConfirmDeleteId(null)
      setEditingItemId(id)
    },
    onCancelEdit: () => setEditingItemId(null),
    onSaved: () => {
      setEditingItemId(null)
      invalidateItems()
    },
  }

  return (
    <PageShell
      title="All Items"
      subtitle={`${activeItems.length} queued`}
      onBack={onBack}
      actions={
        <>
          <a
            href={ITEMS_CSV_URL}
            download
            title="Download all items as CSV"
            aria-label="Download all items as CSV"
            className="inline-flex h-8 items-center justify-center gap-1.5 rounded-xl px-3 text-base transition-all duration-200 hover:bg-black/5 active:scale-[0.98] dark:hover:bg-white/5"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            <span>CSV</span>
          </a>
          <CaptureBox />
        </>
      }
    >
      {groupedItems.length === 0 ? (
        <p className="page-body py-16 text-center text-muted">No items yet. Use Capture to add something.</p>
      ) : (
        <div className="space-y-4">
          {groupedItems.map((group, groupIndex) => (
            <motion.section
              key={group.stream.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: groupIndex * 0.04, duration: 0.5, ease }}
              className="stream-group !py-0"
            >
              <StreamQueue group={group} {...rowHandlers} />
            </motion.section>
          ))}
        </div>
      )}
    </PageShell>
  )
}
