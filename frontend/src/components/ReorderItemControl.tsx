import { Button } from '@/components/ui/button'
import { api, type Item } from '@/lib/api'
import { useMutation } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, Loader2 } from 'lucide-react'

interface ReorderItemControlProps {
  item: Item
  canMoveUp: boolean
  canMoveDown: boolean
  onReordered: () => void
}

export function ReorderItemControl({
  item,
  canMoveUp,
  canMoveDown,
  onReordered,
}: ReorderItemControlProps) {
  const mutation = useMutation({
    mutationFn: (direction: 'up' | 'down') => api.reorderItem(item.id, direction),
    onSuccess: onReordered,
  })

  const disabled = mutation.isPending

  return (
    <div className="flex flex-col">
      <Button
        variant="ghost"
        size="md"
        className="h-8 px-2 text-muted opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 disabled:opacity-30"
        aria-label={`Move ${item.title} up`}
        disabled={disabled || !canMoveUp}
        onClick={() => mutation.mutate('up')}
      >
        {mutation.isPending && mutation.variables === 'up' ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ChevronUp className="h-4 w-4" />
        )}
      </Button>
      <Button
        variant="ghost"
        size="md"
        className="h-8 px-2 text-muted opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 disabled:opacity-30"
        aria-label={`Move ${item.title} down`}
        disabled={disabled || !canMoveDown}
        onClick={() => mutation.mutate('down')}
      >
        {mutation.isPending && mutation.variables === 'down' ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </Button>
    </div>
  )
}
