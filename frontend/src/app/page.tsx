'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import type { Project } from '@/lib/types'
import { ProjectTreePanel } from '@/components/project-tree'
import { SceneEditor } from '@/components/scene-editor'
import { BiblePanel } from '@/components/bible-panel'

export default function WorkspacePage() {
  const { projectId, setProjectId } = useWorkspace()

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiFetch<Project[]>('/api/projects'),
  })

  if (!projectId) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-6">Novel Creator</h1>
          <div className="space-y-2">
            {projects?.map((p) => (
              <button
                key={p.id}
                className="block w-64 mx-auto px-4 py-3 border rounded hover:bg-gray-50 text-left"
                onClick={() => setProjectId(p.id)}
              >
                <div className="font-medium">{p.title}</div>
                <div className="text-xs text-gray-400">{p.description}</div>
              </button>
            ))}
            {projects?.length === 0 && (
              <p className="text-gray-400">暂无项目</p>
            )}
          </div>
        </div>
      </main>
    )
  }

  return (
    <div className="flex h-screen">
      {/* Left: Project Tree */}
      <aside className="w-64 border-r overflow-y-auto bg-gray-50">
        <div className="p-2 border-b">
          <button
            className="text-xs text-blue-600 hover:underline"
            onClick={() => setProjectId(null)}
          >
            ← 返回项目列表
          </button>
        </div>
        <ProjectTreePanel />
      </aside>

      {/* Center: Scene Editor */}
      <main className="flex-1 overflow-hidden">
        <SceneEditor />
      </main>

      {/* Right: Bible Panel */}
      <aside className="w-72 border-l overflow-y-auto bg-gray-50">
        <BiblePanel />
      </aside>
    </div>
  )
}
