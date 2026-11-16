import { create } from 'zustand'
import type { FocusRecommendation } from '@/lib/api'

interface AppState {
  focusMode: boolean
  activeFocus: FocusRecommendation | null
  /** Start the 10-minute timer as soon as Focus mode opens. */
  autoStartTimer: boolean
  captureOpen: boolean
  searchOpen: boolean
  setFocusMode: (on: boolean) => void
  setActiveFocus: (focus: FocusRecommendation | null) => void
  enterFocus: (focus: FocusRecommendation, options?: { startTimer?: boolean }) => void
  exitFocus: () => void
  setCaptureOpen: (open: boolean) => void
  setSearchOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  focusMode: false,
  activeFocus: null,
  autoStartTimer: false,
  captureOpen: false,
  searchOpen: false,
  setFocusMode: (focusMode) => set({ focusMode }),
  setActiveFocus: (activeFocus) => set({ activeFocus }),
  enterFocus: (focus, options) =>
    set({ focusMode: true, activeFocus: focus, autoStartTimer: options?.startTimer ?? false }),
  exitFocus: () => set({ focusMode: false, activeFocus: null, autoStartTimer: false }),
  setCaptureOpen: (captureOpen) => set({ captureOpen }),
  setSearchOpen: (searchOpen) => set({ searchOpen }),
}))
