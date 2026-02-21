'use client'

import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { Scene, SceneCard } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
  const [hints, setHints] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  // Fetch scene to restore saved card
  const { data: scene } = useQuery({
    queryKey: ['scene-detail', sceneId],
    queryFn: () => apiFetch<Scene>(`/api/scenes/${sceneId}`),
  })

  // Reset state when scene changes
  const prevSceneRef = useRef(sceneId)
  useEffect(() => {
    if (prevSceneRef.current !== sceneId) {
      prevSceneRef.current = sceneId
      abortRef.current?.abort()
      setSceneCard(null)
      setStreaming(false)
      setStreamText('')
      setError('')
      setHints('')
    }
  }, [sceneId])

  // Restore saved card when scene data loads
  useEffect(() => {
    if (scene?.scene_card && !sceneCard) {
      setSceneCard(scene.scene_card)
    }
  }, [scene, sceneCard])

  // Save card to backend
  const saveCardMutation = useMutation({
    mutationFn: (card: SceneCard) =>
      apiFetch<Scene>(`/api/scenes/${sceneId}/card`, {
        method: 'PUT',
        body: JSON.stringify({ scene_card: card }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['scene-detail', sceneId],
      })
    },
  })

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
      saveCardMutation.mutate(data)
    },
    onError: (e) => setError(e.message),
  })

  const startStreaming = async () => {
    if (!sceneCard) return
    setStreaming(true)
    setStreamText('')
    setError('')

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const resp = await fetch(`${API_BASE}/api/generate/scene-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scene_id: sceneId,
          scene_card: sceneCard,
        }),
        signal: controller.signal,
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
          try {
            const data = JSON.parse(line.slice(6))
            if (data.done) {
              onDraftComplete(accumulated)
            } else if (data.text) {
              accumulated += data.text
              setStreamText(accumulated)
            }
          } catch {
            continue
          }
        }
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      setError(e instanceof Error ? e.message : '生成失败')
    } finally {
      setStreaming(false)
      queryClient.invalidateQueries({
        queryKey: ['scene-version', sceneId],
      })
    }
  }

  // Save edits to backend when user modifies the card
  const updateCard = (updated: SceneCard) => {
    setSceneCard(updated)
    saveCardMutation.mutate(updated)
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {/* Step 1: Generate Scene Card */}
      {!sceneCard && (
        <div className="space-y-2">
          <textarea
            className="w-full px-2 py-1.5 border border-slate-200 rounded text-xs
              text-slate-700 resize-none focus:outline-none focus:border-blue-400
              placeholder:text-slate-400"
            rows={2}
            placeholder="场景提示（可选）：如 '描写林远在启航前夜的紧张与期待'"
            value={hints}
            onChange={(e) => setHints(e.target.value)}
          />
          <button
            className="w-full text-xs px-3 py-2 bg-blue-600 text-white
              rounded hover:bg-blue-700 disabled:opacity-50 cursor-pointer
              transition-colors"
            disabled={cardMutation.isPending}
            onClick={() => cardMutation.mutate(hints)}
          >
            {cardMutation.isPending ? '生成中...' : '生成场景卡'}
          </button>
        </div>
      )}

      {/* Display & Edit Scene Card */}
      {sceneCard && (
        <div className="bg-slate-50 rounded p-2 text-xs space-y-1.5">
          <Field label="标题" value={sceneCard.title}
            onChange={(v) => updateCard({ ...sceneCard, title: v })} />
          <Field label="地点" value={sceneCard.location}
            onChange={(v) => updateCard({ ...sceneCard, location: v })} />
          <Field label="时间" value={sceneCard.time}
            onChange={(v) => updateCard({ ...sceneCard, time: v })} />
          <Field label="人物" value={sceneCard.characters.join('、')}
            onChange={(v) => updateCard({ ...sceneCard, characters: v.split('、').map(s => s.trim()).filter(Boolean) })} />
          <FieldArea label="冲突" value={sceneCard.conflict}
            onChange={(v) => updateCard({ ...sceneCard, conflict: v })} />
          <FieldArea label="转折" value={sceneCard.turning_point}
            onChange={(v) => updateCard({ ...sceneCard, turning_point: v })} />
          <Field label="目标字数" value={String(sceneCard.target_chars)}
            onChange={(v) => updateCard({ ...sceneCard, target_chars: Math.max(100, Math.min(parseInt(v) || 800, 5000)) })} />
        </div>
      )}

      {/* Step 2: Generate Draft */}
      {sceneCard && !streaming && !streamText && (
        <button
          className="w-full text-xs px-3 py-2 bg-green-600 text-white
            rounded hover:bg-green-700 cursor-pointer transition-colors"
          onClick={startStreaming}
        >
          生成正文
        </button>
      )}

      {/* Streaming Output */}
      {streaming && (
        <div className="text-xs text-slate-500 flex items-center gap-2">
          <div className="w-3 h-3 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
          正在生成中...
        </div>
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
          className="text-xs text-slate-400 hover:text-red-500 cursor-pointer"
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

function Field({ label, value, onChange }: {
  label: string; value: string; onChange: (v: string) => void
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="font-medium text-slate-500 w-14 shrink-0">{label}</span>
      <input
        className="flex-1 px-1.5 py-0.5 border border-slate-200 rounded
          text-xs text-slate-700 bg-white focus:outline-none focus:border-blue-400"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

function FieldArea({ label, value, onChange }: {
  label: string; value: string; onChange: (v: string) => void
}) {
  return (
    <div>
      <span className="font-medium text-slate-500 text-xs">{label}</span>
      <textarea
        className="w-full mt-0.5 px-1.5 py-1 border border-slate-200 rounded
          text-xs text-slate-700 bg-white resize-none focus:outline-none
          focus:border-blue-400"
        rows={2}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
