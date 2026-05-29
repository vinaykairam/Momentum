import { Button } from '@/components/ui/button'
import { api, type Stream, type UpdateStreamPayload } from '@/lib/api'
import { useMutation } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

type StreamCategory = NonNullable<UpdateStreamPayload['category']>
type StreamType = NonNullable<UpdateStreamPayload['type']>

function normalizeCategory(category: string): StreamCategory {
  if (category === 'weekday' || category === 'weekend' || category === 'everyday') {
    return category
  }
  return 'everyday'
}

export function EditStreamForm({
  stream,
  isSubStream,
  onCancel,
  onSuccess,
}: {
  stream: Stream
  isSubStream: boolean
  onCancel: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState(stream.name)
  const [description, setDescription] = useState(stream.description ?? '')
  const [category, setCategory] = useState<StreamCategory>(normalizeCategory(stream.category))
  const [type, setType] = useState<StreamType>((stream.type as StreamType) ?? 'short_term')
  const [priorityWeight, setPriorityWeight] = useState(String(stream.priority_weight ?? 1))
  const [active, setActive] = useState(stream.active)

  const mutation = useMutation({
    mutationFn: (payload: UpdateStreamPayload) => api.updateStream(stream.id, payload),
    onSuccess: () => onSuccess(),
  })

  return (
    <form
      className="space-y-4 rounded-xl border border-border/60 p-5"
      onSubmit={(e) => {
        e.preventDefault()
        if (!name.trim()) return
        const weight = Number(priorityWeight)
        mutation.mutate({
          name: name.trim(),
          description: description.trim() || null,
          type,
          priority_weight: Number.isFinite(weight) ? weight : 1,
          active,
          ...(isSubStream ? {} : { category }),
        })
      }}
    >
      <p className="page-label">Edit {isSubStream ? 'sub-stream' : 'stream'}</p>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Stream name"
        className="field-input"
        autoFocus
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        rows={2}
        className="field-input resize-none"
      />
      {!isSubStream && (
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as StreamCategory)}
          className="field-input"
        >
          <option value="weekday">Weekday</option>
          <option value="weekend">Weekend</option>
          <option value="everyday">Every day</option>
        </select>
      )}
      <select value={type} onChange={(e) => setType(e.target.value as StreamType)} className="field-input">
        <option value="short_term">Short term</option>
        <option value="long_term">Long term</option>
      </select>
      <div>
        <label className="page-meta mb-2 block">Priority weight (0.1 – 10)</label>
        <input
          type="number"
          min={0.1}
          max={10}
          step={0.1}
          value={priorityWeight}
          onChange={(e) => setPriorityWeight(e.target.value)}
          className="field-input"
        />
      </div>
      <label className="flex items-center gap-2 page-meta">
        <input
          type="checkbox"
          checked={active}
          onChange={(e) => setActive(e.target.checked)}
          className="rounded border-border"
        />
        Active
      </label>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="md" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="accent" size="md" disabled={!name.trim() || mutation.isPending}>
          {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
        </Button>
      </div>
      {mutation.isError && (
        <p className="page-meta text-critical">
          {mutation.error instanceof Error ? mutation.error.message : 'Failed to update stream'}
        </p>
      )}
    </form>
  )
}
