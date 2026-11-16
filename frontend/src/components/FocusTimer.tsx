import { Button } from '@/components/ui/button'
import { Pause, Play, RotateCcw } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const DEFAULT_SECONDS = 10 * 60

interface FocusTimerProps {
  autoStart?: boolean
}

function chime() {
  try {
    const ctx = new AudioContext()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.frequency.value = 660
    gain.gain.setValueAtTime(0.15, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2)
    osc.connect(gain).connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 1.2)
  } catch {
    // audio unavailable; the on-screen message is enough
  }
}

function format(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

/** A 10-minute "just start" timer. Wall-clock based so it stays right when the tab sleeps. */
export function FocusTimer({ autoStart }: FocusTimerProps) {
  const [remaining, setRemaining] = useState(DEFAULT_SECONDS)
  const [running, setRunning] = useState(Boolean(autoStart))
  const endsAt = useRef<number | null>(autoStart ? Date.now() + DEFAULT_SECONDS * 1000 : null)

  useEffect(() => {
    if (!running) return
    const tick = () => {
      const left = Math.max(0, Math.round(((endsAt.current ?? Date.now()) - Date.now()) / 1000))
      setRemaining(left)
      if (left === 0) {
        setRunning(false)
        endsAt.current = null
        chime()
      }
    }
    tick()
    const id = window.setInterval(tick, 500)
    return () => window.clearInterval(id)
  }, [running])

  const start = () => {
    const seconds = remaining === 0 ? DEFAULT_SECONDS : remaining
    endsAt.current = Date.now() + seconds * 1000
    setRemaining(seconds)
    setRunning(true)
  }
  const pause = () => {
    setRunning(false)
    endsAt.current = null
  }
  const reset = () => {
    pause()
    setRemaining(DEFAULT_SECONDS)
  }

  const done = remaining === 0
  const untouched = !running && remaining === DEFAULT_SECONDS

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className={`tabular-nums text-3xl ${done ? 'text-thriving' : ''}`}>{format(remaining)}</span>
      {running ? (
        <Button variant="outline" size="sm" onClick={pause} className="gap-1.5">
          <Pause className="h-4 w-4" /> Pause
        </Button>
      ) : (
        <Button variant="outline" size="sm" onClick={start} className="gap-1.5">
          <Play className="h-4 w-4" /> {untouched ? 'Start 10 min' : done ? 'Another 10' : 'Resume'}
        </Button>
      )}
      {!untouched && !done && (
        <Button variant="ghost" size="sm" onClick={reset} className="gap-1.5 text-muted">
          <RotateCcw className="h-4 w-4" /> Reset
        </Button>
      )}
      {done && <span className="page-meta">10 minutes in. Keep going, or log where you got to.</span>}
    </div>
  )
}
