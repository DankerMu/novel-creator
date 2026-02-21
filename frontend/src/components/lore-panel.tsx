'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import { useState } from 'react'

interface LoreEntry {
  id: number
  project_id: number
  type: string
  title: string
  aliases: string[]
  content_md: string
  secrets_md: string
  triggers: { keywords: string[]; and_keywords: string[] }
  priority: number
  locked: boolean
  created_at: string
  updated_at: string
}

const TYPES = ['Character', 'Location', 'Item', 'Concept', 'Rule', 'Organization', 'Event']
const TYPE_COLORS: Record<string, string> = {
  Character: 'bg-blue-100 text-blue-700',
  Location: 'bg-green-100 text-green-700',
  Item: 'bg-amber-100 text-amber-700',
  Concept: 'bg-purple-100 text-purple-700',
  Rule: 'bg-red-100 text-red-700',
  Organization: 'bg-cyan-100 text-cyan-700',
  Event: 'bg-pink-100 text-pink-700',
}

export function LorePanel() {
  const { projectId } = useWorkspace()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [form, setForm] = useState(emptyForm())
  const [error, setError] = useState('')

  const { data: entries } = useQuery({
    queryKey: ['lore-entries', projectId],
    queryFn: () => apiFetch<LoreEntry[]>(`/api/lore?project_id=${projectId}`),
    enabled: !!projectId,
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body = {
        project_id: projectId,
        type: form.type,
        title: form.title,
        aliases: form.aliases.split('、').map(s => s.trim()).filter(Boolean),
        content_md: form.content_md,
        secrets_md: form.secrets_md,
        triggers: {
          keywords: form.keywords.split('、').map(s => s.trim()).filter(Boolean),
          and_keywords: form.and_keywords.split('、').map(s => s.trim()).filter(Boolean),
        },
        priority: form.priority,
        locked: form.locked,
      }
      if (editingId === 'new') {
        return apiFetch('/api/lore', { method: 'POST', body: JSON.stringify(body) })
      } else {
        const { project_id: _, ...updateBody } = body
        return apiFetch(`/api/lore/${editingId}`, { method: 'PUT', body: JSON.stringify(updateBody) })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lore-entries', projectId] })
      setEditingId(null)
      setError('')
    },
    onError: (e) => setError(e instanceof Error ? e.message : '保存失败'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiFetch(`/api/lore/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lore-entries', projectId] })
      setEditingId(null)
    },
    onError: (e) => setError(e instanceof Error ? e.message : '删除失败'),
  })

  const handleExport = async () => {
    const data = await apiFetch<unknown>(`/api/lore/export?project_id=${projectId}`)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'lorebook.json'
    a.click()
    setTimeout(() => URL.revokeObjectURL(a.href), 60_000)
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      const text = await file.text()
      let data: unknown
      try {
        data = JSON.parse(text)
      } catch {
        setError('导入失败：JSON 格式错误')
        return
      }
      try {
        const payload = data as Record<string, unknown>
        await apiFetch('/api/lore/import', {
          method: 'POST',
          body: JSON.stringify({ project_id: projectId, entries: payload.entries ?? payload }),
        })
        queryClient.invalidateQueries({ queryKey: ['lore-entries', projectId] })
      } catch (err) {
        setError(err instanceof Error ? err.message : '导入失败')
      }
    }
    input.click()
  }

  const startEdit = (entry: LoreEntry) => {
    setEditingId(entry.id)
    setForm({
      type: entry.type,
      title: entry.title,
      aliases: entry.aliases.join('、'),
      content_md: entry.content_md,
      secrets_md: entry.secrets_md,
      keywords: entry.triggers.keywords.join('、'),
      and_keywords: entry.triggers.and_keywords.join('、'),
      priority: entry.priority,
      locked: entry.locked,
    })
  }

  const startNew = () => {
    setEditingId('new')
    setForm(emptyForm())
  }

  if (!projectId) return null

  // Group entries by type
  const grouped = (entries ?? []).reduce((acc, e) => {
    ;(acc[e.type] ??= []).push(e)
    return acc
  }, {} as Record<string, LoreEntry[]>)

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{error}</div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          className="flex-1 text-xs px-2 py-1.5 bg-blue-600 text-white rounded
            hover:bg-blue-700 cursor-pointer transition-colors"
          onClick={startNew}
        >
          新建条目
        </button>
        <button
          className="text-xs px-2 py-1.5 border border-slate-300 rounded
            hover:bg-slate-50 cursor-pointer transition-colors"
          onClick={handleImport}
        >
          导入
        </button>
        <button
          className="text-xs px-2 py-1.5 border border-slate-300 rounded
            hover:bg-slate-50 cursor-pointer transition-colors"
          onClick={handleExport}
        >
          导出
        </button>
      </div>

      {/* New/Edit form */}
      {editingId !== null && (
        <div className="border border-blue-200 rounded p-2 space-y-2 bg-blue-50/30">
          <div className="flex gap-2">
            <select
              className="text-xs border border-slate-200 rounded px-1.5 py-1 bg-white"
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
            >
              {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <input
              className="flex-1 text-xs border border-slate-200 rounded px-1.5 py-1
                focus:outline-none focus:border-blue-400"
              placeholder="标题"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>
          <input
            className="w-full text-xs border border-slate-200 rounded px-1.5 py-1
              focus:outline-none focus:border-blue-400"
            placeholder="别名（顿号分隔）"
            value={form.aliases}
            onChange={(e) => setForm({ ...form, aliases: e.target.value })}
          />
          <textarea
            className="w-full text-xs border border-slate-200 rounded px-1.5 py-1
              resize-none focus:outline-none focus:border-blue-400"
            rows={3}
            placeholder="内容（注入到 Context Pack）"
            value={form.content_md}
            onChange={(e) => setForm({ ...form, content_md: e.target.value })}
          />
          <textarea
            className="w-full text-xs border border-slate-200 rounded px-1.5 py-1
              resize-none focus:outline-none focus:border-blue-400"
            rows={2}
            placeholder="作者备注（不注入，仅作者可见）"
            value={form.secrets_md}
            onChange={(e) => setForm({ ...form, secrets_md: e.target.value })}
          />
          <input
            className="w-full text-xs border border-slate-200 rounded px-1.5 py-1
              focus:outline-none focus:border-blue-400"
            placeholder="触发关键词（顿号分隔，任一匹配即触发）"
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
          />
          <input
            className="w-full text-xs border border-slate-200 rounded px-1.5 py-1
              focus:outline-none focus:border-blue-400"
            placeholder="AND 关键词（顿号分隔，全部匹配才触发）"
            value={form.and_keywords}
            onChange={(e) => setForm({ ...form, and_keywords: e.target.value })}
          />
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-500 flex items-center gap-1">
              优先级
              <input
                type="number"
                min={1}
                max={10}
                className="w-12 border border-slate-200 rounded px-1 py-0.5 text-center
                  focus:outline-none focus:border-blue-400"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: Math.max(1, Math.min(10, parseInt(e.target.value) || 5)) })}
              />
            </label>
            <label className="text-xs text-slate-500 flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={form.locked}
                onChange={(e) => setForm({ ...form, locked: e.target.checked })}
              />
              始终注入
            </label>
          </div>
          <div className="flex gap-2">
            <button
              className="flex-1 text-xs px-2 py-1.5 bg-blue-600 text-white rounded
                hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
              disabled={!form.title || saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              {saveMutation.isPending ? '保存中...' : '保存'}
            </button>
            {editingId !== 'new' && (
              <button
                className="text-xs px-2 py-1.5 bg-red-600 text-white rounded
                  hover:bg-red-700 cursor-pointer"
                onClick={() => {
                  if (confirm('确定删除？')) deleteMutation.mutate(editingId as number)
                }}
              >
                删除
              </button>
            )}
            <button
              className="text-xs px-2 py-1.5 border border-slate-300 rounded
                hover:bg-slate-50 cursor-pointer"
              onClick={() => setEditingId(null)}
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* Entry list grouped by type */}
      {Object.entries(grouped).map(([type, items]) => (
        <div key={type}>
          <div className="text-xs font-medium text-slate-500 mb-1">
            {type} ({items.length})
          </div>
          <div className="space-y-1">
            {items.map((entry) => (
              <button
                key={entry.id}
                className={`w-full text-left px-2 py-1.5 rounded text-xs
                  hover:bg-slate-100 cursor-pointer transition-colors ${
                  editingId === entry.id ? 'bg-blue-50 border border-blue-200' : 'bg-white border border-slate-100'
                }`}
                onClick={() => startEdit(entry)}
              >
                <div className="flex items-center gap-1.5">
                  <span className={`px-1 py-0.5 rounded text-[10px] ${TYPE_COLORS[entry.type] ?? 'bg-slate-100 text-slate-600'}`}>
                    {entry.type}
                  </span>
                  <span className="font-medium text-slate-700 truncate">{entry.title}</span>
                  <span className="ml-auto text-slate-400 text-[10px]">P{entry.priority}</span>
                  {entry.locked && <span className="text-[10px]">🔒</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}

      {(entries?.length ?? 0) === 0 && editingId === null && (
        <div className="text-center text-xs text-slate-400 py-6">
          暂无 Lorebook 条目
        </div>
      )}
    </div>
  )
}

function emptyForm() {
  return {
    type: 'Character',
    title: '',
    aliases: '',
    content_md: '',
    secrets_md: '',
    keywords: '',
    and_keywords: '',
    priority: 5,
    locked: false,
  }
}
