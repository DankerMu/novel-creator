import { create } from 'zustand'

interface WorkspaceState {
  projectId: number | null
  selectedSceneId: number | null
  setProjectId: (id: number | null) => void
  selectScene: (id: number | null) => void
}

export const useWorkspace = create<WorkspaceState>((set) => ({
  projectId: null,
  selectedSceneId: null,
  setProjectId: (id) => set({ projectId: id, selectedSceneId: null }),
  selectScene: (id) => set({ selectedSceneId: id }),
}))
