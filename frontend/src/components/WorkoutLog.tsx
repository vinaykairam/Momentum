import type { Item, WorkoutLogEntry } from '@/lib/api'
import { Plus, X } from 'lucide-react'

/** Starting log: what was saved before, else one row per planned set, prefilled with the targets. */
export function initialWorkoutLog(item: Item): WorkoutLogEntry[] {
  if (item.workout_log?.length) return item.workout_log
  return (item.workout_plan ?? []).map((exercise) => {
    const targetReps = parseInt(exercise.reps, 10)
    return {
      exercise: exercise.name,
      sets: Array.from({ length: exercise.sets }, () => ({
        reps: Number.isFinite(targetReps) ? targetReps : null,
        weight: exercise.weight_lb ?? null,
      })),
    }
  })
}

/** Drops empty sets and exercises before saving. */
export function cleanWorkoutLog(log: WorkoutLogEntry[]): WorkoutLogEntry[] {
  return log
    .map((entry) => ({
      exercise: entry.exercise.trim(),
      sets: entry.sets.filter((set) => set.reps !== null || set.weight !== null),
    }))
    .filter((entry) => entry.exercise && entry.sets.length > 0)
}

function toNumber(value: string): number | null {
  if (value.trim() === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null
}

const numberInput =
  'w-16 rounded-lg border border-border bg-transparent px-2 py-1.5 text-center text-base tabular-nums outline-none focus:ring-2 focus:ring-accent/30'

interface WorkoutLogProps {
  value: WorkoutLogEntry[]
  onChange: (log: WorkoutLogEntry[]) => void
  plan?: Item['workout_plan']
  disabled?: boolean
}

/** Reps and weight per set, entered after the workout. Next workouts progress from these numbers. */
export function WorkoutLog({ value, onChange, plan, disabled }: WorkoutLogProps) {
  const update = (index: number, entry: WorkoutLogEntry) =>
    onChange(value.map((current, i) => (i === index ? entry : current)))

  return (
    <div className="space-y-5">
      {value.map((entry, index) => {
        const target = plan?.find((p) => p.name === entry.exercise)
        return (
          <div key={index} className="rounded-xl border border-border/60 p-4">
            <div className="flex items-center gap-2">
              <input
                value={entry.exercise}
                onChange={(e) => update(index, { ...entry, exercise: e.target.value })}
                placeholder="Exercise"
                disabled={disabled}
                className="min-w-0 flex-1 bg-transparent text-lg outline-none"
              />
              <button
                type="button"
                aria-label={`Remove ${entry.exercise || 'exercise'}`}
                onClick={() => onChange(value.filter((_, i) => i !== index))}
                disabled={disabled}
                className="text-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {target && (
              <p className="page-meta mt-0.5 text-sm">
                Target {target.sets} × {target.reps}
                {target.weight_lb ? ` @ ${target.weight_lb} lb` : ''}
              </p>
            )}
            <div className="mt-3 space-y-2">
              {entry.sets.map((set, setIndex) => (
                <div key={setIndex} className="flex items-center gap-2 text-base">
                  <span className="page-meta w-12 shrink-0">Set {setIndex + 1}</span>
                  <input
                    inputMode="decimal"
                    aria-label={`Set ${setIndex + 1} reps`}
                    value={set.reps ?? ''}
                    onChange={(e) =>
                      update(index, {
                        ...entry,
                        sets: entry.sets.map((s, i) => (i === setIndex ? { ...s, reps: toNumber(e.target.value) } : s)),
                      })
                    }
                    disabled={disabled}
                    className={numberInput}
                  />
                  <span className="page-meta">reps/sec</span>
                  <input
                    inputMode="decimal"
                    aria-label={`Set ${setIndex + 1} weight in pounds`}
                    value={set.weight ?? ''}
                    placeholder="—"
                    onChange={(e) =>
                      update(index, {
                        ...entry,
                        sets: entry.sets.map((s, i) => (i === setIndex ? { ...s, weight: toNumber(e.target.value) } : s)),
                      })
                    }
                    disabled={disabled}
                    className={numberInput}
                  />
                  <span className="page-meta">lb</span>
                  <button
                    type="button"
                    aria-label={`Remove set ${setIndex + 1}`}
                    onClick={() => update(index, { ...entry, sets: entry.sets.filter((_, i) => i !== setIndex) })}
                    disabled={disabled}
                    className="ml-auto text-muted hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => {
                const last = entry.sets[entry.sets.length - 1]
                update(index, { ...entry, sets: [...entry.sets, { reps: last?.reps ?? null, weight: last?.weight ?? null }] })
              }}
              disabled={disabled}
              className="page-meta mt-3 inline-flex items-center gap-1 hover:text-foreground"
            >
              <Plus className="h-4 w-4" /> Add set
            </button>
          </div>
        )
      })}
      <button
        type="button"
        onClick={() => onChange([...value, { exercise: '', sets: [{ reps: null, weight: null }] }])}
        disabled={disabled}
        className="page-meta inline-flex items-center gap-1 hover:text-foreground"
      >
        <Plus className="h-4 w-4" /> Add exercise
      </button>
    </div>
  )
}
