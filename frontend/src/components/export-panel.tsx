'use client'

import { useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function ExportPanel({
  bookId,
  chapterId,
}: {
  bookId: number
  chapterId?: number
}) {
  const [exporting, setExporting] = useState(false)

  const handleExport = async (format: 'markdown' | 'txt') => {
    setExporting(true)
    try {
      let url = `${API_BASE}/api/export/${format}?book_id=${bookId}`
      if (chapterId) {
        url += `&chapter_id=${chapterId}`
      }

      const resp = await fetch(url)
      if (!resp.ok) throw new Error('导出失败')

      const text = await resp.text()
      const ext = format === 'markdown' ? 'md' : 'txt'
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `export.${ext}`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch {
      alert('导出失败')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="border rounded p-3 space-y-2">
      <h3 className="font-bold text-sm">导出</h3>
      <p className="text-xs text-gray-500">
        {chapterId ? '导出当前章节' : '导出整本书'}
      </p>
      <div className="flex gap-2">
        <button
          className="text-xs px-3 py-1.5 bg-gray-700 text-white
            rounded disabled:opacity-50"
          disabled={exporting}
          onClick={() => handleExport('markdown')}
        >
          Markdown
        </button>
        <button
          className="text-xs px-3 py-1.5 bg-gray-700 text-white
            rounded disabled:opacity-50"
          disabled={exporting}
          onClick={() => handleExport('txt')}
        >
          纯文本
        </button>
      </div>
    </div>
  )
}
