'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import { useState } from 'react'

interface BibleField {
  id: number
  project_id: number
  key: string
  value_md: string
  locked: boolean
  updated_at: string
}

export function BiblePanel() {
  const { projectId } = useWorkspace()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')

  const { data: fields } = useQuery({
    queryKey: ['bible', projectId],
    queryFn: () =>
      apiFetch<BibleField[]>(`/api/bible?project_id=${projectId}`),
    enabled: !!projectId,
  })

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number
      data: { value_md?: string; locked?: boolean }
    }) =>
      apiFetch<BibleField>(`/api/bible/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bible', projectId] })
      setEditingId(null)
    },
  })

  if (!projectId) return null

  return (
    <div className="p-3 space-y-3 text-sm">
      <h2 className="font-bold text-base">Story Bible</h2>
      {fields?.map((field) => (
        <div key={field.id} className="border rounded p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium text-xs">
              {field.key}
            </span>
            <button
              className={`text-xs px-1.5 py-0.5 rounded ${
                field.locked
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-500'
              }`}
              onClick={() =>
                updateMutation.mutate({
                  id: field.id,
                  data: { locked: !field.locked },
                })
              }
            >
              {field.locked ? '🔒 已锁定' : '🔓 未锁定'}
            </button>
          </div>
          {editingId === field.id ? (
            <div>
              <textarea
                className="w-full border rounded p-1 text-xs"
                rows={3}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
              />
              <div className="flex gap-1 mt-1">
                <button
                  className="text-xs px-2 py-0.5 bg-blue-600
                    text-white rounded"
                  onClick={() =>
                    updateMutation.mutate({
                      id: field.id,
                      data: { value_md: editValue },
                    })
                  }
                >
                  保存
                </button>
                <button
                  className="text-xs px-2 py-0.5 border rounded"
                  onClick={() => setEditingId(null)}
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <div
              className="text-xs text-gray-600 cursor-pointer
                hover:bg-gray-50 rounded p-1 min-h-[24px]"
              onClick={() => {
                setEditingId(field.id)
                setEditValue(field.value_md)
              }}
            >
              {field.value_md || '点击编辑...'}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
