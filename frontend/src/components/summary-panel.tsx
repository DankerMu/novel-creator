'use client'

import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ChapterSummary {
  id: number
  chapter_id: number
  summary_md: string
  key_events: string[]
  keywords: string[]
  entities: string[]
  plot_threads: string[]
  created_at: string
}

export function SummaryPanel({
  chapterId,
}: {
  chapterId: number
}) {
  const [markingDone, setMarkingDone] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [dirty, setDirty] = useState(false)

  // Editable local state
  const [editSummary, setEditSummary] = useState('')
  const [editKeyEvents, setEditKeyEvents] = useState('')
  const [editKeywords, setEditKeywords] = useState('')
  const [editEntities, setEditEntities] = useState('')
  const [editPlotThreads, setEditPlotThreads] = useState('')

  const { data: summary, refetch } = useQuery({
    queryKey: ['chapter-summary', chapterId],
    queryFn: async () => {
      const resp = await fetch(
        `${API_BASE}/api/chapters/${chapterId}/summary`
      )
      if (resp.status === 404) return null
      if (!resp.ok) throw new Error('Failed to fetch summary')
      return resp.json() as Promise<ChapterSummary>
    },
    enabled: !!chapterId,
  })

  // Sync fetched summary to local editable state
  useEffect(() => {
    if (summary) {
      setEditSummary(summary.summary_md)
      setEditKeyEvents(summary.key_events.join('\n'))
      setEditKeywords(summary.keywords.join('、'))
      setEditEntities(summary.entities.join('、'))
      setEditPlotThreads(summary.plot_threads.join('\n'))
      setDirty(false)
    } else {
      setEditSummary('')
      setEditKeyEvents('')
      setEditKeywords('')
      setEditEntities('')
      setEditPlotThreads('')
      setDirty(false)
    }
  }, [summary])

  const handleMarkDone = async () => {
    setMarkingDone(true)
    setError('')
    try {
      const resp = await fetch(
        `${API_BASE}/api/chapters/${chapterId}/mark-done`,
        { method: 'POST' }
      )
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || '标记完成失败')
      }
      await refetch()
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作失败')
    } finally {
      setMarkingDone(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      const resp = await fetch(
        `${API_BASE}/api/chapters/${chapterId}/summary`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            summary_md: editSummary,
            key_events: editKeyEvents.split('\n').map(s => s.trim()).filter(Boolean),
            keywords: editKeywords.split('、').map(s => s.trim()).filter(Boolean),
            entities: editEntities.split('、').map(s => s.trim()).filter(Boolean),
            plot_threads: editPlotThreads.split('\n').map(s => s.trim()).filter(Boolean),
          }),
        }
      )
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || '保存失败')
      }
      setDirty(false)
      await refetch()
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const markDirty = () => setDirty(true)

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {!summary && (
        <div>
          <p className="text-xs text-slate-500 mb-2">
            标记章节完成后将自动生成摘要
          </p>
          <button
            className="w-full text-xs px-3 py-2 bg-orange-600 text-white
              rounded hover:bg-orange-700 disabled:opacity-50
              cursor-pointer transition-colors"
            disabled={markingDone}
            onClick={handleMarkDone}
          >
            {markingDone ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                生成中...
              </span>
            ) : '标记完成并生成摘要'}
          </button>
        </div>
      )}

      {summary && (
        <div className="space-y-3 text-xs">
          {/* Editable summary */}
          <div>
            <label className="font-medium text-slate-500">叙事总结</label>
            <textarea
              className="w-full mt-1 px-2 py-1.5 border border-slate-200 rounded
                text-slate-700 bg-white resize-none focus:outline-none
                focus:border-blue-400"
              rows={4}
              value={editSummary}
              onChange={(e) => { setEditSummary(e.target.value); markDirty() }}
            />
          </div>

          {/* Editable key events (one per line) */}
          <div>
            <label className="font-medium text-slate-500">关键事件（每行一个）</label>
            <textarea
              className="w-full mt-1 px-2 py-1.5 border border-slate-200 rounded
                text-slate-700 bg-white resize-none focus:outline-none
                focus:border-blue-400"
              rows={3}
              value={editKeyEvents}
              onChange={(e) => { setEditKeyEvents(e.target.value); markDirty() }}
            />
          </div>

          {/* Editable keywords (separator: 、) */}
          <div>
            <label className="font-medium text-slate-500">关键词（顿号分隔）</label>
            <input
              className="w-full mt-1 px-2 py-1.5 border border-slate-200 rounded
                text-slate-700 bg-white focus:outline-none focus:border-blue-400"
              value={editKeywords}
              onChange={(e) => { setEditKeywords(e.target.value); markDirty() }}
            />
          </div>

          {/* Editable entities (separator: 、) */}
          <div>
            <label className="font-medium text-slate-500">实体（顿号分隔）</label>
            <input
              className="w-full mt-1 px-2 py-1.5 border border-slate-200 rounded
                text-slate-700 bg-white focus:outline-none focus:border-blue-400"
              value={editEntities}
              onChange={(e) => { setEditEntities(e.target.value); markDirty() }}
            />
          </div>

          {/* Editable plot threads (one per line) */}
          <div>
            <label className="font-medium text-slate-500">情节线索（每行一个）</label>
            <textarea
              className="w-full mt-1 px-2 py-1.5 border border-slate-200 rounded
                text-slate-700 bg-white resize-none focus:outline-none
                focus:border-blue-400"
              rows={3}
              value={editPlotThreads}
              onChange={(e) => { setEditPlotThreads(e.target.value); markDirty() }}
            />
          </div>

          {/* Save button */}
          {dirty && (
            <button
              className="w-full text-xs px-3 py-2 bg-blue-600 text-white
                rounded hover:bg-blue-700 disabled:opacity-50
                cursor-pointer transition-colors"
              disabled={saving}
              onClick={handleSave}
            >
              {saving ? '保存中...' : '保存修改'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
