import { create } from 'zustand'
import type { FocusRecommendation } from '@/lib/api'

interface AppState {
  focusMode: boolean
  activeFocus: FocusRecommendation | null
  captureOpen: boolean
  searchOpen: boolean
  setFocusMode: (on: boolean) => void
  setActiveFocus: (focus: FocusRecommendation | null) => void
  enterFocus: (focus: FocusRecommendation) => void
  exitFocus: () => void
  setCaptureOpen: (open: boolean) => void
  setSearchOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  focusMode: false,
  activeFocus: null,
  captureOpen: false,
  searchOpen: false,
  setFocusMode: (focusMode) => set({ focusMode }),
  setActiveFocus: (activeFocus) => set({ activeFocus }),
  enterFocus: (focus) => set({ focusMode: true, activeFocus: focus }),
  exitFocus: () => set({ focusMode: false, activeFocus: null }),
  setCaptureOpen: (captureOpen) => set({ captureOpen }),
  setSearchOpen: (searchOpen) => set({ searchOpen }),
}))
