'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
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
import { useMemo, useState } from 'react'

type RightTab = 'generate' | 'summary' | 'bible' | 'lore' | 'export'

export default function WorkspacePage() {
  const {
    projectId, setProjectId,
    selectedSceneId, selectedChapterId, selectedBookId,
  } = useWorkspace()
  const queryClient = useQueryClient()
  const [rightTab, setRightTab] = useState<RightTab>('generate')

  const { data: projects, isLoading: loadingProjects, error: projectsError } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiFetch<Project[]>('/api/projects'),
  })

  const { data: tree } = useQuery({
    queryKey: ['project-tree', projectId],
    queryFn: () => apiFetch<ProjectTree>(`/api/projects/${projectId}/tree`),
    enabled: !!projectId,
  })

  const { bookTitle, chapterTitle } = useMemo(() => {
    if (!tree || !selectedBookId) return { bookTitle: undefined, chapterTitle: undefined }
    const book = tree.books.find((b) => b.id === selectedBookId)
    const chapter = book?.chapters.find((c) => c.id === selectedChapterId)
    return { bookTitle: book?.title, chapterTitle: chapter?.title }
  }, [tree, selectedBookId, selectedChapterId])

  // ---------- Project selection screen ----------
  if (!projectId) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="w-full max-w-md mx-auto px-4">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Novel Creator</h1>
            <p className="text-sm text-slate-500 mt-2">中文中长篇小说 AI 写作平台</p>
          </div>

          {loadingProjects && (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-slate-400 mt-3">加载项目列表...</p>
            </div>
          )}

          {projectsError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <p className="text-sm text-red-600">无法连接后端服务</p>
              <p className="text-xs text-red-400 mt-1">请确认 http://localhost:8000 正在运行</p>
            </div>
          )}

          {!loadingProjects && !projectsError && (
            <div className="space-y-2">
              {projects?.map((p) => (
                <button
                  key={p.id}
                  className="block w-full px-4 py-3 bg-white border border-slate-200
                    rounded-lg hover:border-blue-400 hover:shadow-sm
                    transition-all duration-150 text-left cursor-pointer"
                  onClick={() => setProjectId(p.id)}
                >
                  <div className="font-medium text-slate-800">{p.title}</div>
                  {p.description && (
                    <div className="text-xs text-slate-400 mt-0.5">{p.description}</div>
                  )}
                </button>
              ))}
              {projects?.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-slate-400">暂无项目</p>
                  <p className="text-xs text-slate-400 mt-1">通过 API 创建: POST /api/projects</p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    )
  }

  // ---------- Workspace layout ----------
  const tabs: { key: RightTab; label: string }[] = [
    { key: 'generate', label: 'AI 生成' },
    { key: 'summary', label: '摘要' },
    { key: 'bible', label: '设定' },
    { key: 'lore', label: 'Lore' },
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
