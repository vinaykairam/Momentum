import { EditItemForm } from '@/components/EditItemForm'
import { MoveItemControl } from '@/components/MoveItemControl'
import { ReorderItemControl } from '@/components/ReorderItemControl'
import { Button } from '@/components/ui/button'
import type { Item, Stream } from '@/lib/api'
import { statusLabel } from '@/lib/item-queue'
import { Loader2, Pencil, Trash2 } from 'lucide-react'

interface ItemRowProps {
  item: Item
  streams: Stream[]
  queuePosition: number
  canMoveUp: boolean
  canMoveDown: boolean
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
}

export function ItemRow({
  item,
  streams,
  queuePosition,
  canMoveUp,
  canMoveDown,
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
}: ItemRowProps) {
  if (editingItemId === item.id) {
    return (
      <div className="py-5 md:py-6">
        <EditItemForm item={item} streams={streams} onCancel={onCancelEdit} onSuccess={onSaved} />
      </div>
    )
  }

  return (
    <div className="group flex items-start justify-between gap-4 py-5 md:py-6">
      <div className="min-w-0 flex-1">
        <p className="page-meta">
          #{queuePosition} · {item.item_type.replace('_', ' ')} · {statusLabel(item.status)}
        </p>
        <h2 className="page-body mt-1.5">{item.title}</h2>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="page-meta mt-1.5 block truncate hover:text-foreground"
          >
            {item.url}
          </a>
        )}
      </div>

      <div className="shrink-0 pt-1">
        {confirmDeleteId === item.id ? (
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="md" onClick={onCancelDelete} disabled={isDeleting}>
              Cancel
            </Button>
            <Button
              variant="default"
              size="md"
              className="bg-critical hover:opacity-90"
              disabled={isDeleting}
              onClick={() => onDelete(item.id)}
            >
              {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Delete'}
            </Button>
          </div>
        ) : (
          <div className="flex items-start gap-0.5">
            <ReorderItemControl
              item={item}
              canMoveUp={canMoveUp}
              canMoveDown={canMoveDown}
              onReordered={onMoved}
            />
            <MoveItemControl item={item} streams={streams} onMoved={onMoved} />
            <Button
              variant="ghost"
              size="md"
              onClick={() => onEdit(item.id)}
              className="text-muted opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100"
              aria-label={`Edit ${item.title}`}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="md"
              onClick={() => onConfirmDelete(item.id)}
              className="text-muted opacity-0 transition-opacity hover:text-critical group-hover:opacity-100"
              aria-label={`Delete ${item.title}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
