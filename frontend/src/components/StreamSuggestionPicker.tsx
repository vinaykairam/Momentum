import type { StreamSuggestion } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Loader2, Sparkles } from 'lucide-react'

interface StreamSuggestionPickerProps {
  suggestion: StreamSuggestion | null
  isLoading: boolean
  waitingForMoreInput?: boolean
  selectedStreamId: number | ''
  onSelect: (streamId: number) => void
}

export function StreamSuggestionPicker({
  suggestion,
  isLoading,
  waitingForMoreInput = false,
  selectedStreamId,
  onSelect,
}: StreamSuggestionPickerProps) {
  if (waitingForMoreInput) {
    return <p className="page-meta">Keep typing for stream suggestions…</p>
  }

  if (isLoading) {
    return (
      <p className="page-meta flex items-center gap-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Finding the best stream…
      </p>
    )
  }

  if (!suggestion) {
    return null
  }

  if (suggestion.status === 'unavailable') {
    return <p className="page-meta">{suggestion.reasoning}</p>
  }

  if (suggestion.status === 'ambiguous' && suggestion.options.length > 0) {
    return (
      <div className="space-y-3">
        <p className="page-meta">This could fit a few streams — pick one:</p>
        <div className="flex flex-col gap-2">
          {suggestion.options.map((option) => {
            const selected = selectedStreamId === option.stream_id
            return (
              <button
                key={option.stream_id}
                type="button"
                onClick={() => onSelect(option.stream_id)}
                className={cn(
                  'rounded-xl border px-4 py-3 text-left transition-colors',
                  selected
                    ? 'border-accent bg-accent-soft'
                    : 'border-[var(--color-border)] hover:bg-black/5 dark:hover:bg-white/5',
                )}
              >
                <span className="font-medium">{option.stream_name}</span>
                <span className="page-meta mt-1 block">{option.reason}</span>
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  if (suggestion.recommended) {
    const selected = selectedStreamId === suggestion.recommended.stream_id
    return (
      <button
        type="button"
        onClick={() => onSelect(suggestion.recommended!.stream_id)}
        className={cn(
          'flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors',
          selected
            ? 'border-accent bg-accent-soft'
            : 'border-[var(--color-border)] hover:bg-black/5 dark:hover:bg-white/5',
        )}
      >
        <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent opacity-80" />
        <span>
          <span className="page-meta block">Suggested stream</span>
          <span className="font-medium">{suggestion.recommended.stream_name}</span>
          <span className="page-meta mt-1 block">{suggestion.reasoning}</span>
        </span>
      </button>
    )
  }

  return null
}
