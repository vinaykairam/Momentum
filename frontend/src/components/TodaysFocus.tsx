import { FocusCard } from '@/components/FocusCard'
import type { FocusRecommendation } from '@/lib/api'
import { groupFocusRecommendations } from '@/lib/focus-groups'
import { motion } from 'framer-motion'

interface TodaysFocusProps {
  focus: FocusRecommendation[]
}

const ease = [0.25, 0.1, 0.25, 1] as const

export function TodaysFocus({ focus }: TodaysFocusProps) {
  if (focus.length === 0) {
    return (
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, ease }}
        className="page-body py-16 text-center text-muted"
      >
        Nothing queued for today.
      </motion.p>
    )
  }

  const groups = groupFocusRecommendations(focus)

  return (
    <div>
      {groups.length > 0 && (
        <div className="-mx-6 flex snap-x snap-mandatory items-start gap-4 overflow-x-auto px-6 pb-4 md:snap-none">
          {groups.map((group, groupIndex) => (
            <motion.section
              key={group.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: groupIndex * 0.06, duration: 0.5, ease }}
              className="stream-group w-[85vw] max-w-md shrink-0 snap-start md:w-auto md:min-w-[18rem] md:max-w-none md:flex-1"
            >
              {group.isGrouped && <p className="stream-group-title">{group.parentName}</p>}
              <div className={group.isGrouped ? 'stream-group-items' : undefined}>
                {group.items.map((item, itemIndex) => (
                  <FocusCard
                    key={`${item.stream_id}-${item.item_id}`}
                    focus={item}
                    index={groupIndex + itemIndex}
                    nested={group.isGrouped}
                  />
                ))}
              </div>
            </motion.section>
          ))}
        </div>
      )}
    </div>
  )
}
