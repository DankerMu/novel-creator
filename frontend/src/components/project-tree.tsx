'use client'

import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import type { Book, Chapter, ProjectTree, Scene } from '@/lib/types'

type AddingTarget =
  | { type: 'book' }
  | { type: 'chapter'; bookId: number }
  | { type: 'scene'; chapterId: number }
  | null

export function ProjectTreePanel() {
  const { projectId, selectedSceneId, selectScene } = useWorkspace()
  const queryClient = useQueryClient()
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [adding, setAdding] = useState<AddingTarget>(null)
  const [newTitle, setNewTitle] = useState('')
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (adding) inputRef.current?.focus()
  }, [adding])

  const { data: tree } = useQuery({
    queryKey: ['project-tree', projectId],
    queryFn: () => apiFetch<ProjectTree>(`/api/projects/${projectId}/tree`),
    enabled: !!projectId,
  })

  const toggle = (key: string) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const invalidateTree = () => {
    queryClient.invalidateQueries({ queryKey: ['project-tree', projectId] })
  }

  const resetAdding = () => {
    setAdding(null)
    setNewTitle('')
  }

  const onMutationError = () => {
    setError('创建失败，请重试')
    setTimeout(() => setError(''), 3000)
  }

  const createBook = useMutation({
    mutationFn: (title: string) =>
      apiFetch<Book>('/api/books', {
        method: 'POST',
        body: JSON.stringify({ project_id: projectId, title }),
      }),
    onSuccess: () => { invalidateTree(); resetAdding() },
    onError: onMutationError,
  })

  const createChapter = useMutation({
    mutationFn: ({ bookId, title }: { bookId: number; title: string }) =>
      apiFetch<Chapter>('/api/chapters', {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId, title }),
      }),
    onSuccess: () => { invalidateTree(); resetAdding() },
    onError: onMutationError,
  })

  const createScene = useMutation({
    mutationFn: ({ chapterId, title }: { chapterId: number; title: string }) =>
      apiFetch<Scene>('/api/scenes', {
        method: 'POST',
        body: JSON.stringify({ chapter_id: chapterId, title }),
      }),
    onSuccess: () => { invalidateTree(); resetAdding() },
    onError: onMutationError,
  })

  const handleSubmit = () => {
    const t = newTitle.trim()
    if (!t || !adding) return
    if (adding.type === 'book') createBook.mutate(t)
    else if (adding.type === 'chapter') createChapter.mutate({ bookId: adding.bookId, title: t })
    else createScene.mutate({ chapterId: adding.chapterId, title: t })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSubmit()
    else if (e.key === 'Escape') resetAdding()
  }

  const handleBlur = () => {
    if (newTitle.trim()) handleSubmit()
    else resetAdding()
  }

  const startAdding = (target: AddingTarget) => {
    setAdding(target)
    setNewTitle('')
    setError('')
  }

  if (!projectId) {
    return <div className="p-4 text-gray-400">请选择项目</div>
  }

  if (!tree) {
    return <div className="p-4 text-gray-400">加载中...</div>
  }

  const isPending = createBook.isPending || createChapter.isPending || createScene.isPending

  return (
    <div className="p-2 text-sm">
      {error && (
        <div className="text-xs text-red-600 bg-red-50 rounded p-1.5 mb-2 mx-1">
          {error}
        </div>
      )}
      <h2 className="font-bold text-base mb-2 px-2">{tree.title}</h2>

      {tree.books.map((book) => (
        <div key={book.id}>
          <button
            className="w-full text-left px-2 py-1 font-semibold hover:bg-gray-100 rounded"
            onClick={() => toggle(`book-${book.id}`)}
          >
            {collapsed[`book-${book.id}`] ? '▶' : '▼'} {book.title}
          </button>

          {!collapsed[`book-${book.id}`] && (
            <>
              {book.chapters.map((chapter) => (
                <div key={chapter.id} className="ml-3">
                  <button
                    className="w-full text-left px-2 py-0.5 hover:bg-gray-100 rounded flex items-center gap-1"
                    onClick={() => toggle(`ch-${chapter.id}`)}
                  >
                    {collapsed[`ch-${chapter.id}`] ? '▶' : '▼'}
                    <span>{chapter.title}</span>
                    {chapter.status === 'done' && (
                      <span className="text-green-600 text-xs">✓</span>
                    )}
                  </button>

                  {!collapsed[`ch-${chapter.id}`] && (
                    <>
                      {chapter.scenes.map((scene) => (
                        <button
                          key={scene.id}
                          className={`w-full text-left ml-4 px-2 py-0.5 rounded text-xs ${
                            selectedSceneId === scene.id
                              ? 'bg-blue-100 text-blue-700 font-medium'
                              : 'hover:bg-gray-50'
                          }`}
                          onClick={() => selectScene(scene.id, chapter.id, book.id)}
                        >
                          {scene.title}
                        </button>
                      ))}

                      {/* Inline: add scene */}
                      {adding?.type === 'scene' && adding.chapterId === chapter.id ? (
                        <div className="ml-4 mt-0.5">
                          <input
                            ref={inputRef}
                            className="w-full border border-blue-300 rounded px-2 py-0.5 text-xs
                              focus:outline-none focus:border-blue-500"
                            placeholder="场景标题"
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onBlur={handleBlur}
                            disabled={isPending}
                          />
                        </div>
                      ) : (
                        <button
                          className="w-full text-left ml-4 px-2 py-0.5 text-xs text-slate-400
                            hover:text-blue-600 cursor-pointer"
                          onClick={() => startAdding({ type: 'scene', chapterId: chapter.id })}
                        >
                          + 新建场景
                        </button>
                      )}
                    </>
                  )}
                </div>
              ))}

              {/* Inline: add chapter */}
              {adding?.type === 'chapter' && adding.bookId === book.id ? (
                <div className="ml-3 mt-0.5">
                  <input
                    ref={inputRef}
                    className="w-full border border-blue-300 rounded px-2 py-0.5 text-sm
                      focus:outline-none focus:border-blue-500"
                    placeholder="章节标题"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onBlur={() => { if (!newTitle.trim()) resetAdding() }}
                    disabled={isPending}
                  />
                </div>
              ) : (
                <button
                  className="w-full text-left ml-3 px-2 py-0.5 text-xs text-slate-400
                    hover:text-blue-600 cursor-pointer"
                  onClick={() => startAdding({ type: 'chapter', bookId: book.id })}
                >
                  + 新建章节
                </button>
              )}
            </>
          )}
        </div>
      ))}

      {/* Inline: add book */}
      {adding?.type === 'book' ? (
        <div className="mt-1">
          <input
            ref={inputRef}
            className="w-full border border-blue-300 rounded px-2 py-1 text-sm
              focus:outline-none focus:border-blue-500"
            placeholder="卷标题"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => { if (!newTitle.trim()) resetAdding() }}
            disabled={isPending}
          />
        </div>
      ) : (
        <button
          className="w-full text-left px-2 py-1 mt-1 text-xs text-slate-400
            hover:text-blue-600 cursor-pointer"
          onClick={() => startAdding({ type: 'book' })}
        >
          + 新建卷
        </button>
      )}
    </div>
  )
}
