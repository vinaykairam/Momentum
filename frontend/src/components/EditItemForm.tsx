import { StreamSelect } from '@/components/StreamSelect'
import { Button } from '@/components/ui/button'
import { api, type Item, type Stream, type UpdateItemPayload } from '@/lib/api'
import { useMutation } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

const ITEM_TYPES = [
  'task',
  'project',
  'youtube',
  'article',
  'course',
  'note',
  'bookmark',
  'idea',
  'pdf',
  'resource',
  'link',
  'video',
  'document',
] as const

const STATUSES = ['backlog', 'next', 'active', 'completed', 'archived'] as const
const IMPORTANCE = ['low', 'medium', 'high'] as const
const EFFORT = ['tiny', 'small', 'medium', 'large'] as const

function label(value: string): string {
  return value.replace('_', ' ')
}

export function EditItemForm({
  item,
  streams,
  onCancel,
  onSuccess,
}: {
  item: Item
  streams: Stream[]
  onCancel: () => void
  onSuccess: () => void
}) {
  const [title, setTitle] = useState(item.title)
  const [url, setUrl] = useState(item.url ?? '')
  const [description, setDescription] = useState(item.description ?? '')
  const [notes, setNotes] = useState(item.notes ?? '')
  const [streamId, setStreamId] = useState<number | ''>(item.stream_id)
  const [itemType, setItemType] = useState(item.item_type)
  const [status, setStatus] = useState(item.status)
  const [importance, setImportance] = useState(item.importance)
  const [effortEstimate, setEffortEstimate] = useState(item.effort_estimate)
  const [estimatedDuration, setEstimatedDuration] = useState(
    item.estimated_duration != null ? String(item.estimated_duration) : '',
  )

  const mutation = useMutation({
    mutationFn: (payload: UpdateItemPayload) => api.updateItem(item.id, payload),
    onSuccess: () => onSuccess(),
  })

  return (
    <form
      className="space-y-4 rounded-xl border border-border/60 p-5"
      onSubmit={(e) => {
        e.preventDefault()
        if (!title.trim() || streamId === '') return
        const duration = estimatedDuration.trim() ? Number(estimatedDuration) : null
        mutation.mutate({
          title: title.trim(),
          url: url.trim() || null,
          description: description.trim() || null,
          notes: notes.trim() || null,
          stream_id: streamId,
          item_type: itemType,
          status,
          importance,
          effort_estimate: effortEstimate,
          estimated_duration: duration != null && Number.isFinite(duration) && duration >= 1 ? duration : null,
        })
      }}
    >
      <p className="page-label">Edit item</p>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title"
        className="field-input"
        autoFocus
      />
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="URL (optional)"
        className="field-input"
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        rows={2}
        className="field-input resize-none"
      />
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes (optional)"
        rows={2}
        className="field-input resize-none"
      />
      <div>
        <label className="page-meta mb-2 block">Stream</label>
        <StreamSelect streams={streams} value={streamId} onChange={setStreamId} disabled={mutation.isPending} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="page-meta mb-2 block">Type</label>
          <select
            value={itemType}
            onChange={(e) => setItemType(e.target.value)}
            className="field-input"
            disabled={mutation.isPending}
          >
            {ITEM_TYPES.map((type) => (
              <option key={type} value={type}>
                {label(type)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="page-meta mb-2 block">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="field-input"
            disabled={mutation.isPending}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {label(s)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="page-meta mb-2 block">Importance</label>
          <select
            value={importance}
            onChange={(e) => setImportance(e.target.value)}
            className="field-input"
            disabled={mutation.isPending}
          >
            {IMPORTANCE.map((level) => (
              <option key={level} value={level}>
                {label(level)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="page-meta mb-2 block">Effort</label>
          <select
            value={effortEstimate}
            onChange={(e) => setEffortEstimate(e.target.value)}
            className="field-input"
            disabled={mutation.isPending}
          >
            {EFFORT.map((level) => (
              <option key={level} value={level}>
                {label(level)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="page-meta mb-2 block">Estimated duration (minutes, optional)</label>
        <input
          type="number"
          min={1}
          value={estimatedDuration}
          onChange={(e) => setEstimatedDuration(e.target.value)}
          className="field-input"
          disabled={mutation.isPending}
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="md" onClick={onCancel} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button
          type="submit"
          variant="accent"
          size="md"
          disabled={!title.trim() || streamId === '' || mutation.isPending}
        >
          {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
        </Button>
      </div>
      {mutation.isError && (
        <p className="page-meta text-critical">
          {mutation.error instanceof Error ? mutation.error.message : 'Failed to update item'}
        </p>
      )}
    </form>
  )
}
