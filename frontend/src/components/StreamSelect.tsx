import { getStreamPath } from '@/lib/utils'
import { buildStreamOptions } from '@/lib/stream-options'
import type { Stream } from '@/lib/api'

interface StreamSelectProps {
  streams: Stream[]
  value: number | ''
  onChange: (value: number | '') => void
  disabled?: boolean
  excludeStreamId?: number
}

export function StreamSelect({ streams, value, onChange, disabled, excludeStreamId }: StreamSelectProps) {
  const options = buildStreamOptions(streams).filter((option) => option.id !== excludeStreamId)

  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : '')}
      className="field-input disabled:opacity-50"
    >
      <option value="">Select a stream</option>
      {options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.depth > 0 ? `  ${option.label}` : option.label}
        </option>
      ))}
    </select>
  )
}

export function streamLabel(streams: Stream[], streamId: number): string {
  return getStreamPath(streamId, streams)
}
