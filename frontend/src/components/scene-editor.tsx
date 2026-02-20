'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import type { SceneVersion } from '@/lib/types'
import { useState, useEffect } from 'react'

export function SceneEditor() {
  const { selectedSceneId } = useWorkspace()
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [dirty, setDirty] = useState(false)

  const { data: version } = useQuery({
    queryKey: ['scene-version', selectedSceneId],
    queryFn: () => apiFetch<SceneVersion>(`/api/scenes/${selectedSceneId}/versions/latest`),
    enabled: !!selectedSceneId,
  })

  useEffect(() => {
    if (version) {
      setContent(version.content_md)
      setDirty(false)
    }
  }, [version])

  const saveMutation = useMutation({
    mutationFn: () =>
      apiFetch<SceneVersion>(`/api/scenes/${selectedSceneId}/versions`, {
        method: 'POST',
        body: JSON.stringify({ content_md: content }),
      }),
    onSuccess: () => {
      setDirty(false)
      queryClient.invalidateQueries({ queryKey: ['scene-version', selectedSceneId] })
    },
  })

  if (!selectedSceneId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        从左侧项目树选择一个场景开始编辑
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <div className="text-sm text-gray-500">
          版本 {version?.version ?? '-'} · {content.length} 字
        </div>
        <button
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded disabled:opacity-50"
          disabled={!dirty || saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
        >
          {saveMutation.isPending ? '保存中...' : '保存'}
        </button>
      </div>
      <textarea
        className="flex-1 p-4 resize-none outline-none font-mono text-sm leading-relaxed"
        value={content}
        onChange={(e) => {
          setContent(e.target.value)
          setDirty(true)
        }}
        placeholder="在此编辑场景内容..."
      />
    </div>
  )
}
