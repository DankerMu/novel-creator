'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import type { Project, ProjectTree } from '@/lib/types'
import { ProjectTreePanel } from '@/components/project-tree'
import { SceneEditor } from '@/components/scene-editor'
import { BiblePanel } from '@/components/bible-panel'
import { GeneratePanel } from '@/components/generate-panel'
import { SummaryPanel } from '@/components/summary-panel'
import { ExportPanel } from '@/components/export-panel'
import { LorePanel } from '@/components/lore-panel'
import { KGPanel } from '@/components/kg-panel'

type RightTab = 'generate' | 'summary' | 'bible' | 'lore' | 'kg' | 'export'

interface BibleField {
  id: number
  key: string
  value_md: string
  locked: boolean
}

const GENRE_OPTIONS = ['玄幻', '都市', '科幻', '历史', '言情', '悬疑', '其他']
const STYLE_OPTIONS = ['严肃文学', '轻小说', '网文', '纯文学']
const POV_OPTIONS = ['第一人称', '第三人称有限', '第三人称全知', '多视角']
const TENSE_OPTIONS = ['过去式', '现在式']

export default function WorkspacePage() {
  const {
    projectId, setProjectId,
    selectedSceneId, selectedChapterId, selectedBookId,
  } = useWorkspace()
  const queryClient = useQueryClient()
  const [rightTab, setRightTab] = useState<RightTab>('generate')
  const [showCreateModal, setShowCreateModal] = useState(false)

  const {
    data: projects, isLoading: loadingProjects, error: projectsError,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiFetch<Project[]>('/api/projects'),
  })

  const { data: tree } = useQuery({
    queryKey: ['project-tree', projectId],
    queryFn: () => apiFetch<ProjectTree>(
      `/api/projects/${projectId}/tree`
    ),
    enabled: !!projectId,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/api/projects/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const { bookTitle, chapterTitle } = useMemo(() => {
    if (!tree || !selectedBookId)
      return { bookTitle: undefined, chapterTitle: undefined }
    const book = tree.books.find((b) => b.id === selectedBookId)
    const chapter = book?.chapters.find(
      (c) => c.id === selectedChapterId
    )
    return { bookTitle: book?.title, chapterTitle: chapter?.title }
  }, [tree, selectedBookId, selectedChapterId])

  const handleDelete = (e: React.MouseEvent, p: Project) => {
    e.stopPropagation()
    if (!window.confirm(`确定删除「${p.title}」？此操作不可撤销。`))
      return
    deleteMutation.mutate(p.id)
  }

  // ---------- Project selection screen ----------
  if (!projectId) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="w-full max-w-md mx-auto px-4">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight">
              Novel Creator
            </h1>
            <p className="text-sm text-slate-500 mt-2">
              中文中长篇小说 AI 写作平台
            </p>
          </div>

          {loadingProjects && (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-slate-400 mt-3">
                加载项目列表...
              </p>
            </div>
          )}

          {projectsError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <p className="text-sm text-red-600">无法连接后端服务</p>
              <p className="text-xs text-red-400 mt-1">
                请确认 http://localhost:8000 正在运行
              </p>
            </div>
          )}

          {!loadingProjects && !projectsError && (
            <div className="space-y-2">
              {projects?.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center gap-2 bg-white border
                    border-slate-200 rounded-lg hover:border-blue-400
                    hover:shadow-sm transition-all duration-150"
                >
                  <button
                    className="flex-1 px-4 py-3 text-left cursor-pointer"
                    onClick={() => setProjectId(p.id)}
                  >
                    <div className="font-medium text-slate-800">
                      {p.title}
                    </div>
                    {p.description && (
                      <div className="text-xs text-slate-400 mt-0.5">
                        {p.description}
                      </div>
                    )}
                  </button>
                  <button
                    className="p-2 mr-2 text-slate-300 hover:text-red-500
                      transition-colors cursor-pointer"
                    title="删除项目"
                    onClick={(e) => handleDelete(e, p)}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}

              {projects?.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-slate-400">暂无项目</p>
                  <p className="text-xs text-slate-400 mt-1">
                    点击下方按钮创建你的第一部小说
                  </p>
                </div>
              )}

              <button
                className="block w-full px-4 py-3 border-2 border-dashed
                  border-slate-300 rounded-lg text-sm text-slate-500
                  hover:border-blue-400 hover:text-blue-600
                  transition-colors cursor-pointer"
                onClick={() => setShowCreateModal(true)}
              >
                <svg className="w-4 h-4 inline-block mr-1 -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                新建小说
              </button>
            </div>
          )}
        </div>

        {showCreateModal && (
          <CreateProjectModal
            onClose={() => setShowCreateModal(false)}
            onCreated={(id) => {
              setShowCreateModal(false)
              queryClient.invalidateQueries({ queryKey: ['projects'] })
              setProjectId(id)
            }}
          />
        )}
      </main>
    )
  }

  // ---------- Workspace layout ----------
  const tabs: { key: RightTab; label: string }[] = [
    { key: 'generate', label: 'AI 生成' },
    { key: 'summary', label: '摘要' },
    { key: 'bible', label: '设定' },
    { key: 'lore', label: 'Lore' },
    { key: 'kg', label: 'KG' },
    { key: 'export', label: '导出' },
  ]

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top Bar */}
      <header className="h-11 flex items-center justify-between px-4 border-b border-slate-200 bg-white shrink-0">
        <div className="flex items-center gap-3">
          <button
            className="text-xs text-blue-600 hover:text-blue-800 cursor-pointer"
            onClick={() => setProjectId(null)}
          >
            <svg className="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            返回
          </button>
          <span className="text-sm font-semibold text-slate-700">
            {tree?.title ?? '加载中...'}
          </span>
        </div>
        <span className="text-xs text-slate-400">Novel Creator v0.1</span>
      </header>

      {/* Three Column Layout */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Project Tree */}
        <aside className="w-60 border-r border-slate-200 overflow-y-auto bg-white shrink-0">
          <ProjectTreePanel />
        </aside>

        {/* Center: Scene Editor */}
        <main className="flex-1 min-w-0 overflow-hidden">
          <SceneEditor />
        </main>

        {/* Right: Tabbed Panels */}
        <aside className="w-80 border-l border-slate-200 bg-white shrink-0 flex flex-col min-h-0">
          {/* Tab Buttons */}
          <div className="flex border-b border-slate-200 shrink-0">
            {tabs.map((t) => (
              <button
                key={t.key}
                className={`flex-1 py-2 text-xs font-medium transition-colors cursor-pointer ${
                  rightTab === t.key
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                    : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                }`}
                onClick={() => setRightTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab Content — all panels stay mounted to preserve state */}
          <div className={`flex-1 overflow-y-auto p-3 ${rightTab === 'generate' ? '' : 'hidden'}`}>
            {selectedSceneId && selectedChapterId ? (
              <GeneratePanel
                sceneId={selectedSceneId}
                chapterId={selectedChapterId}
                onDraftComplete={async (text) => {
                  await apiFetch(`/api/scenes/${selectedSceneId}/versions`, {
                    method: 'POST',
                    body: JSON.stringify({ content_md: text, created_by: 'ai' }),
                  })
                  queryClient.invalidateQueries({
                    queryKey: ['scene-version', selectedSceneId],
                  })
                }}
              />
            ) : (
              <EmptyHint text="选择一个场景以使用 AI 生成" />
            )}
          </div>

          <div className={`flex-1 overflow-y-auto p-3 ${rightTab === 'summary' ? '' : 'hidden'}`}>
            {selectedChapterId ? (
              <SummaryPanel chapterId={selectedChapterId} />
            ) : (
              <EmptyHint text="选择一个章节以查看摘要" />
            )}
          </div>

          <div className={`flex-1 overflow-y-auto p-3 ${rightTab === 'bible' ? '' : 'hidden'}`}>
            <BiblePanel />
          </div>

          <div className={`flex-1 overflow-y-auto p-3 ${rightTab === 'lore' ? '' : 'hidden'}`}>
            <LorePanel />
          </div>

          <div className={`flex-1 overflow-y-auto p-3 ${rightTab === 'kg' ? '' : 'hidden'}`}>
            {projectId ? (
              <KGPanel />
            ) : (
              <EmptyHint text="选择一个项目以使用 KG 审阅" />
            )}
          </div>

          <div className={`flex-1 overflow-y-auto p-3 ${rightTab === 'export' ? '' : 'hidden'}`}>
            {selectedBookId ? (
              <ExportPanel
                bookId={selectedBookId}
                bookTitle={bookTitle}
                chapterId={selectedChapterId ?? undefined}
                chapterTitle={chapterTitle}
              />
            ) : (
              <EmptyHint text="选择一个书籍以导出" />
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center h-32 text-sm text-slate-400">
      {text}
    </div>
  )
}

// ---------- Create Project Modal ----------

function CreateProjectModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (projectId: number) => void
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [genre, setGenre] = useState('')
  const [style, setStyle] = useState('')
  const [pov, setPov] = useState('')
  const [tense, setTense] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const handleCreate = async () => {
    if (!title.trim()) {
      setError('请输入小说标题')
      return
    }
    setCreating(true)
    setError('')
    try {
      const project = await apiFetch<Project>('/api/projects', {
        method: 'POST',
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
        }),
      })

      // Set bible presets if any selected
      const presets: Record<string, string> = {}
      if (genre) presets['Genre'] = genre
      if (style) presets['Style'] = style
      if (pov) presets['POV'] = pov
      if (tense) presets['Tense'] = tense

      if (Object.keys(presets).length > 0) {
        const fields = await apiFetch<BibleField[]>(
          `/api/bible?project_id=${project.id}`
        )
        for (const field of fields) {
          const val = presets[field.key]
          if (val) {
            await apiFetch(`/api/bible/${field.id}`, {
              method: 'PUT',
              body: JSON.stringify({ value_md: val }),
            })
          }
        }
      }

      onCreated(project.id)
    } catch {
      setError('创建失败，请重试')
      setCreating(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center
        justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-md
          mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          新建小说
        </h2>

        {error && (
          <div className="text-xs text-red-600 bg-red-50 rounded
            p-2 mb-3">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              标题 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              className="w-full border border-slate-300 rounded-lg
                px-3 py-2 text-sm focus:outline-none
                focus:border-blue-500"
              placeholder="输入小说标题"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              简介
            </label>
            <textarea
              className="w-full border border-slate-300 rounded-lg
                px-3 py-2 text-sm focus:outline-none
                focus:border-blue-500"
              rows={2}
              placeholder="简单描述你的小说（可选）"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <PresetSelect
              label="类型"
              value={genre}
              onChange={setGenre}
              options={GENRE_OPTIONS}
            />
            <PresetSelect
              label="风格"
              value={style}
              onChange={setStyle}
              options={STYLE_OPTIONS}
            />
            <PresetSelect
              label="叙事视角"
              value={pov}
              onChange={setPov}
              options={POV_OPTIONS}
            />
            <PresetSelect
              label="时态"
              value={tense}
              onChange={setTense}
              options={TENSE_OPTIONS}
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            className="px-4 py-2 text-sm border border-slate-300
              rounded-lg hover:bg-slate-50 transition-colors
              cursor-pointer"
            onClick={onClose}
            disabled={creating}
          >
            取消
          </button>
          <button
            className="px-4 py-2 text-sm bg-blue-600 text-white
              rounded-lg hover:bg-blue-700 transition-colors
              disabled:opacity-50 cursor-pointer"
            onClick={handleCreate}
            disabled={creating}
          >
            {creating ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </div>
  )
}

function PresetSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: string[]
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-600 mb-1">
        {label}
      </label>
      <select
        className="w-full border border-slate-300 rounded-lg
          px-3 py-2 text-sm focus:outline-none
          focus:border-blue-500 bg-white"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">不限</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  )
}
