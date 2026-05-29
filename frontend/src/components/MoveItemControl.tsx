import { StreamSelect } from '@/components/StreamSelect'
import { Button } from '@/components/ui/button'
import { api, type Item, type Stream } from '@/lib/api'
import { useMutation } from '@tanstack/react-query'
import { ArrowRightLeft, Loader2 } from 'lucide-react'
import { useState } from 'react'

interface MoveItemControlProps {
  item: Item
  streams: Stream[]
  onMoved: () => void
}

export function MoveItemControl({ item, streams, onMoved }: MoveItemControlProps) {
  const [open, setOpen] = useState(false)
  const [targetStreamId, setTargetStreamId] = useState<number | ''>(item.stream_id)

  const mutation = useMutation({
    mutationFn: (streamId: number) => api.updateItem(item.id, { stream_id: streamId }),
    onSuccess: () => {
      setOpen(false)
      onMoved()
    },
  })

  if (open) {
    return (
      <div className="flex min-w-[12rem] flex-col items-end gap-2 sm:min-w-[14rem]">
        <StreamSelect
          streams={streams}
          value={targetStreamId}
          onChange={setTargetStreamId}
          disabled={mutation.isPending}
          excludeStreamId={item.stream_id}
        />
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="md"
            onClick={() => {
              setOpen(false)
              setTargetStreamId(item.stream_id)
            }}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="accent"
            size="md"
            disabled={
              mutation.isPending || targetStreamId === '' || targetStreamId === item.stream_id
            }
            onClick={() => targetStreamId !== '' && mutation.mutate(targetStreamId)}
          >
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Move'}
          </Button>
        </div>
        {mutation.isError && (
          <p className="page-meta text-right text-critical">
            {mutation.error instanceof Error ? mutation.error.message : 'Could not move item'}
          </p>
        )}
      </div>
    )
  }

  return (
    <Button
      variant="ghost"
      size="md"
      onClick={() => {
        setTargetStreamId('')
        setOpen(true)
      }}
      className="text-muted opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100"
      aria-label={`Move ${item.title}`}
    >
      <ArrowRightLeft className="h-4 w-4" />
    </Button>
  )
}
