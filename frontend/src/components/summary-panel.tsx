'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ChapterSummary {
  id: number
  chapter_id: number
  summary_md: string
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
  const [error, setError] = useState('')

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

  return (
    <div className="border rounded p-3 space-y-3">
      <h3 className="font-bold text-sm">章节摘要</h3>

      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {!summary && (
        <div>
          <p className="text-xs text-gray-500 mb-2">
            标记章节完成后将自动生成摘要
          </p>
          <button
            className="text-xs px-3 py-1.5 bg-orange-600 text-white
              rounded disabled:opacity-50"
            disabled={markingDone}
            onClick={handleMarkDone}
          >
            {markingDone ? '生成中...' : '标记完成并生成摘要'}
          </button>
        </div>
      )}

      {summary && (
        <div className="space-y-2 text-xs">
          <div className="bg-gray-50 rounded p-2 whitespace-pre-wrap">
            {summary.summary_md}
          </div>

          {summary.keywords.length > 0 && (
            <div>
              <b>关键词:</b>
              <div className="flex flex-wrap gap-1 mt-1">
                {summary.keywords.map((kw) => (
                  <span
                    key={kw}
                    className="bg-blue-100 text-blue-700 px-1.5
                      py-0.5 rounded"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {summary.entities.length > 0 && (
            <div>
              <b>实体:</b>
              <div className="flex flex-wrap gap-1 mt-1">
                {summary.entities.map((ent) => (
                  <span
                    key={ent}
                    className="bg-green-100 text-green-700 px-1.5
                      py-0.5 rounded"
                  >
                    {ent}
                  </span>
                ))}
              </div>
            </div>
          )}

          {summary.plot_threads.length > 0 && (
            <div>
              <b>情节线索:</b>
              <ul className="list-disc list-inside mt-1">
                {summary.plot_threads.map((pt) => (
                  <li key={pt}>{pt}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
