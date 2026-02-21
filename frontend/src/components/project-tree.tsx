'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import type { ProjectTree } from '@/lib/types'
import { useState } from 'react'

export function ProjectTreePanel() {
  const { projectId, selectedSceneId, selectScene } = useWorkspace()
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const { data: tree } = useQuery({
    queryKey: ['project-tree', projectId],
    queryFn: () => apiFetch<ProjectTree>(`/api/projects/${projectId}/tree`),
    enabled: !!projectId,
  })

  const toggle = (key: string) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  if (!projectId) {
    return <div className="p-4 text-gray-400">请选择项目</div>
  }

  if (!tree) {
    return <div className="p-4 text-gray-400">加载中...</div>
  }

  return (
    <div className="p-2 text-sm">
      <h2 className="font-bold text-base mb-2 px-2">{tree.title}</h2>
      {tree.books.map((book) => (
        <div key={book.id}>
          <button
            className="w-full text-left px-2 py-1 font-semibold hover:bg-gray-100 rounded"
            onClick={() => toggle(`book-${book.id}`)}
          >
            {collapsed[`book-${book.id}`] ? '▶' : '▼'} {book.title}
          </button>
          {!collapsed[`book-${book.id}`] && book.chapters.map((chapter) => (
            <div key={chapter.id} className="ml-3">
              <button
                className="w-full text-left px-2 py-0.5 hover:bg-gray-100 rounded flex items-center gap-1"
                onClick={() => toggle(`ch-${chapter.id}`)}
              >
                {collapsed[`ch-${chapter.id}`] ? '▶' : '▼'}
                <span>{chapter.title}</span>
                {chapter.status === 'done' && (
                  <span className="text-green-600 text-xs">✓</span>
                )}
              </button>
              {!collapsed[`ch-${chapter.id}`] && chapter.scenes.map((scene) => (
                <button
                  key={scene.id}
                  className={`w-full text-left ml-4 px-2 py-0.5 rounded text-xs ${
                    selectedSceneId === scene.id
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => selectScene(scene.id, chapter.id, book.id)}
                >
                  {scene.title}
                </button>
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
