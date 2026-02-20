'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useWorkspace } from '@/hooks/use-workspace'
import { useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface SceneCard {
  title: string
  location: string
  time: string
  characters: string[]
  conflict: string
  turning_point: string
  reveal: string
  target_chars: number
}

export function GeneratePanel({
  sceneId,
  chapterId,
  onDraftComplete,
}: {
  sceneId: number
  chapterId: number
  onDraftComplete: (text: string) => void
}) {
  const queryClient = useQueryClient()
  const [sceneCard, setSceneCard] = useState<SceneCard | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [streamText, setStreamText] = useState('')
  const [error, setError] = useState('')

  const cardMutation = useMutation({
    mutationFn: async (hints: string) => {
      const resp = await fetch(`${API_BASE}/api/generate/scene-card`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_id: chapterId,
          scene_id: sceneId,
          hints,
        }),
      })
      if (!resp.ok) throw new Error('场景卡生成失败')
      return resp.json() as Promise<SceneCard>
    },
    onSuccess: (data) => {
      setSceneCard(data)
      setError('')
    },
    onError: (e) => setError(e.message),
  })

  const startStreaming = async () => {
    if (!sceneCard) return
    setStreaming(true)
    setStreamText('')
    setError('')

    try {
      const resp = await fetch(`${API_BASE}/api/generate/scene-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scene_id: sceneId,
          scene_card: sceneCard,
        }),
      })

      if (!resp.ok) throw new Error('正文生成失败')
      if (!resp.body) throw new Error('No stream body')

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))
          if (data.done) {
            onDraftComplete(accumulated)
          } else if (data.text) {
            accumulated += data.text
            setStreamText(accumulated)
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败')
    } finally {
      setStreaming(false)
      queryClient.invalidateQueries({
        queryKey: ['scene-version', sceneId],
      })
    }
  }

  return (
    <div className="border rounded p-3 space-y-3">
      <h3 className="font-bold text-sm">AI 生成</h3>

      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {/* Step 1: Generate Scene Card */}
      {!sceneCard && (
        <div>
          <button
            className="text-xs px-3 py-1.5 bg-blue-600 text-white
              rounded disabled:opacity-50"
            disabled={cardMutation.isPending}
            onClick={() => cardMutation.mutate('')}
          >
            {cardMutation.isPending ? '生成中...' : '生成场景卡'}
          </button>
        </div>
      )}

      {/* Display Scene Card */}
      {sceneCard && (
        <div className="bg-gray-50 rounded p-2 text-xs space-y-1">
          <div><b>标题:</b> {sceneCard.title}</div>
          <div><b>地点:</b> {sceneCard.location}</div>
          <div><b>时间:</b> {sceneCard.time}</div>
          <div><b>人物:</b> {sceneCard.characters.join('、')}</div>
          <div><b>冲突:</b> {sceneCard.conflict}</div>
          {sceneCard.turning_point && (
            <div><b>转折:</b> {sceneCard.turning_point}</div>
          )}
          <div><b>目标字数:</b> {sceneCard.target_chars}</div>
        </div>
      )}

      {/* Step 2: Generate Draft */}
      {sceneCard && !streaming && !streamText && (
        <button
          className="text-xs px-3 py-1.5 bg-green-600 text-white
            rounded"
          onClick={startStreaming}
        >
          生成正文
        </button>
      )}

      {/* Streaming Output */}
      {streaming && (
        <div className="text-xs text-gray-500">正在生成中...</div>
      )}
      {streamText && (
        <div className="text-xs bg-white border rounded p-2
          max-h-48 overflow-y-auto whitespace-pre-wrap">
          {streamText}
        </div>
      )}

      {/* Reset */}
      {sceneCard && (
        <button
          className="text-xs text-gray-400 hover:text-gray-600"
          onClick={() => {
            setSceneCard(null)
            setStreamText('')
          }}
        >
          重置
        </button>
      )}
    </div>
  )
}
