import { create } from 'zustand'

interface WorkspaceState {
  projectId: number | null
  selectedSceneId: number | null
  selectedChapterId: number | null
  selectedBookId: number | null
  setProjectId: (id: number | null) => void
  selectScene: (sceneId: number | null, chapterId?: number | null, bookId?: number | null) => void
}

export const useWorkspace = create<WorkspaceState>((set) => ({
  projectId: null,
  selectedSceneId: null,
  selectedChapterId: null,
  selectedBookId: null,
  setProjectId: (id) => set({ projectId: id, selectedSceneId: null, selectedChapterId: null, selectedBookId: null }),
  selectScene: (sceneId, chapterId, bookId) => set({ selectedSceneId: sceneId, selectedChapterId: chapterId ?? null, selectedBookId: bookId ?? null }),
}))
