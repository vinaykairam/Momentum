import { EditStreamForm } from '@/components/EditStreamForm'
import { CaptureBox } from '@/components/CaptureBox'
import { PageLoading, PageShell } from '@/components/PageShell'
import { Button } from '@/components/ui/button'
import { api, type CreateStreamPayload, type Stream } from '@/lib/api'
import { buildStreamTree } from '@/lib/stream-tree'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Loader2, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'

interface StreamsPageProps {
  onBack: () => void
}

type StreamCategory = CreateStreamPayload['category']

const ease = [0.25, 0.1, 0.25, 1] as const

function DeleteStreamButton({
  stream,
  confirmDeleteId,
  isDeleting,
  onConfirm,
  onCancel,
  onDelete,
}: {
  stream: Stream
  confirmDeleteId: number | null
  isDeleting: boolean
  onConfirm: (id: number) => void
  onCancel: () => void
  onDelete: (id: number) => void
}) {
  if (confirmDeleteId === stream.id) {
    return (
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="md" onClick={onCancel} disabled={isDeleting}>
          Cancel
        </Button>
        <Button
          variant="default"
          size="md"
          className="bg-critical hover:opacity-90"
          disabled={isDeleting}
          onClick={() => onDelete(stream.id)}
        >
          {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Delete'}
        </Button>
      </div>
    )
  }

  return (
    <Button
      variant="ghost"
      size="md"
      onClick={() => onConfirm(stream.id)}
      className="text-muted hover:text-critical"
      aria-label={`Delete ${stream.name}`}
    >
      <Trash2 className="h-4 w-4" />
    </Button>
  )
}

function AddStreamForm({
  parentId,
  parentName,
  onCancel,
  onSuccess,
}: {
  parentId?: number
  parentName?: string
  onCancel: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState<StreamCategory>('everyday')

  const mutation = useMutation({
    mutationFn: (payload: CreateStreamPayload) => api.createStream(payload),
    onSuccess: () => {
      setName('')
      setDescription('')
      onSuccess()
    },
  })

  return (
    <form
      className="space-y-4 rounded-xl border border-border/60 p-5"
      onSubmit={(e) => {
        e.preventDefault()
        if (!name.trim()) return
        mutation.mutate({
          name: name.trim(),
          description: description.trim() || null,
          category: parentId ? undefined : category,
          parent_id: parentId ?? null,
        })
      }}
    >
      <p className="page-label">{parentId ? `New sub-stream under ${parentName}` : 'New stream'}</p>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Stream name"
        className="field-input"
        autoFocus
      />
      <input
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        className="field-input"
      />
      {!parentId && (
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
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="md" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="accent" size="md" disabled={!name.trim() || mutation.isPending}>
          {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add'}
        </Button>
      </div>
      {mutation.isError && (
        <p className="page-meta text-critical">
          {mutation.error instanceof Error ? mutation.error.message : 'Failed to create stream'}
        </p>
      )}
    </form>
  )
}

function StreamMeta({ stream }: { stream: Stream }) {
  return (
    <>
      <p className="page-meta mt-1 capitalize">
        {stream.category === 'custom' ? 'every day' : stream.category.replace('_', ' ')} ·{' '}
        {stream.type.replace('_', ' ')}
        {!stream.active && ' · inactive'}
      </p>
      {stream.description && <p className="page-meta mt-1">{stream.description}</p>}
    </>
  )
}

function StreamNodeCard({
  stream,
  subStreams,
  onAddSubStream,
  addingSubStream,
  setAddingSubStream,
  onStreamCreated,
  confirmDeleteId,
  editingStreamId,
  setEditingStreamId,
  isDeleting,
  onConfirmDelete,
  onCancelDelete,
  onDeleteStream,
}: {
  stream: Stream
  subStreams: Stream[]
  onAddSubStream: (id: number) => void
  addingSubStream: number | null
  setAddingSubStream: (id: number | null) => void
  onStreamCreated: () => void
  confirmDeleteId: number | null
  editingStreamId: number | null
  setEditingStreamId: (id: number | null) => void
  isDeleting: boolean
  onConfirmDelete: (id: number) => void
  onCancelDelete: () => void
  onDeleteStream: (id: number) => void
}) {
  const isEditing = editingStreamId === stream.id

  return (
    <div className="py-5 md:py-6">
      {isEditing ? (
        <EditStreamForm
          stream={stream}
          isSubStream={false}
          onCancel={() => setEditingStreamId(null)}
          onSuccess={() => {
            setEditingStreamId(null)
            onStreamCreated()
          }}
        />
      ) : (
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h2 className="page-body">{stream.name}</h2>
            <StreamMeta stream={stream} />
            {subStreams.length > 0 && confirmDeleteId === stream.id && (
              <p className="page-meta mt-2 text-critical">Sub-streams will also be deleted.</p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button variant="outline" size="md" onClick={() => onAddSubStream(stream.id)} className="gap-1.5">
              <Plus className="h-4 w-4" />
              Sub-stream
            </Button>
            <Button
              variant="ghost"
              size="md"
              onClick={() => setEditingStreamId(stream.id)}
              className="text-muted"
              aria-label={`Edit ${stream.name}`}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <DeleteStreamButton
              stream={stream}
              confirmDeleteId={confirmDeleteId}
              isDeleting={isDeleting}
              onConfirm={onConfirmDelete}
              onCancel={onCancelDelete}
              onDelete={onDeleteStream}
            />
          </div>
        </div>
      )}

      {addingSubStream === stream.id && (
        <div className="mt-5">
          <AddStreamForm
            parentId={stream.id}
            parentName={stream.name}
            onCancel={() => setAddingSubStream(null)}
            onSuccess={() => {
              setAddingSubStream(null)
              onStreamCreated()
            }}
          />
        </div>
      )}

      {subStreams.length > 0 && (
        <div className="mt-4 divide-y divide-border/40 border-t border-border/40 pt-2">
          {subStreams.map((child) =>
            editingStreamId === child.id ? (
              <div key={child.id} className="py-4">
                <EditStreamForm
                  stream={child}
                  isSubStream
                  onCancel={() => setEditingStreamId(null)}
                  onSuccess={() => {
                    setEditingStreamId(null)
                    onStreamCreated()
                  }}
                />
              </div>
            ) : (
              <div key={child.id} className="flex items-start justify-between gap-4 py-5">
                <div className="min-w-0 flex-1">
                  <p className="page-label">{child.name}</p>
                  {child.description && <p className="page-meta mt-1">{child.description}</p>}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button
                    variant="ghost"
                    size="md"
                    onClick={() => setEditingStreamId(child.id)}
                    className="text-muted"
                    aria-label={`Edit ${child.name}`}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <DeleteStreamButton
                    stream={child}
                    confirmDeleteId={confirmDeleteId}
                    isDeleting={isDeleting}
                    onConfirm={onConfirmDelete}
                    onCancel={onCancelDelete}
                    onDelete={onDeleteStream}
                  />
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  )
}

export function StreamsPage({ onBack }: StreamsPageProps) {
  const queryClient = useQueryClient()
  const [addingMain, setAddingMain] = useState(false)
  const [addingSubStream, setAddingSubStream] = useState<number | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  const [editingStreamId, setEditingStreamId] = useState<number | null>(null)

  const { data: streams, isLoading, error } = useQuery({
    queryKey: ['streams'],
    queryFn: api.getStreams,
  })

  const deleteMutation = useMutation({
    mutationFn: api.deleteStream,
    onSuccess: () => {
      setConfirmDeleteId(null)
      queryClient.invalidateQueries({ queryKey: ['streams'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['items'] })
    },
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['streams'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  if (isLoading) return <PageLoading />

  if (error || !streams) {
    return (
      <div className="py-20 text-center">
        <p className="page-body text-muted">Unable to load streams</p>
        <Button variant="ghost" size="md" className="mt-4" onClick={onBack}>
          Back
        </Button>
      </div>
    )
  }

  const tree = buildStreamTree(streams)

  return (
    <PageShell
      title="Streams"
      subtitle={`${streams.length} total`}
      onBack={onBack}
      actions={<CaptureBox />}
    >
      <div className="mb-8 flex justify-end">
        <Button variant="accent" size="md" onClick={() => setAddingMain(true)} className="gap-1.5">
          <Plus className="h-4 w-4" />
          Add stream
        </Button>
      </div>

      {addingMain && (
        <div className="mb-8">
          <AddStreamForm
            onCancel={() => setAddingMain(false)}
            onSuccess={() => {
              setAddingMain(false)
              invalidate()
            }}
          />
        </div>
      )}

      <div className="divide-y divide-border/40">
        {tree.map((node, index) => (
          <motion.div
            key={node.stream.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.04, duration: 0.5, ease }}
          >
            <StreamNodeCard
              stream={node.stream}
              subStreams={node.children.map((c) => c.stream)}
              onAddSubStream={setAddingSubStream}
              addingSubStream={addingSubStream}
              setAddingSubStream={setAddingSubStream}
              onStreamCreated={invalidate}
              confirmDeleteId={confirmDeleteId}
              editingStreamId={editingStreamId}
              setEditingStreamId={setEditingStreamId}
              isDeleting={deleteMutation.isPending}
              onConfirmDelete={setConfirmDeleteId}
              onCancelDelete={() => setConfirmDeleteId(null)}
              onDeleteStream={(id) => deleteMutation.mutate(id)}
            />
          </motion.div>
        ))}
      </div>
    </PageShell>
  )
}
