import { MomentumBar } from '@/components/MomentumBar'
import type { Stream } from '@/lib/api'

interface MomentumHealthProps {
  streams: Stream[]
}

export function MomentumHealth({ streams }: MomentumHealthProps) {
  const roots = streams.filter((stream) => !stream.parent_id)

  return (
    <div className="space-y-5">
      {roots.map((stream) => {
        const children = streams.filter((entry) => entry.parent_id === stream.id)

        return (
          <div key={stream.id} className="space-y-3">
            <MomentumBar
              name={stream.name}
              score={stream.momentum_score}
              state={stream.momentum_state}
            />
            {children.map((child) => (
              <div key={child.id} className="ml-5 border-l border-border pl-4">
                <MomentumBar
                  name={child.name}
                  score={child.momentum_score}
                  state={child.momentum_state}
                  nested
                />
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
