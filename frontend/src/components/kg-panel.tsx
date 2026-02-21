'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useWorkspace } from '@/hooks/use-workspace'
import { useEffect, useState } from 'react'
import type { KGProposal } from '@/lib/types'

// Status display mapping
const STATUS_LABELS: Record<string, string> = {
  pending: '待审阅',
  auto_approved: '已通过',
  user_approved: '已通过',
  rejected: '已拒绝',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-700',
  auto_approved: 'bg-green-100 text-green-700',
  user_approved: 'bg-green-100 text-green-700',
  rejected: 'bg-slate-100 text-slate-500',
}

const CATEGORY_COLORS: Record<string, string> = {
  entity: 'bg-blue-100 text-blue-700',
  relation: 'bg-purple-100 text-purple-700',
  event: 'bg-pink-100 text-pink-700',
}

const CATEGORY_LABELS: Record<string, string> = {
  entity: '实体',
  relation: '关系',
  event: '事件',
}

type StatusFilter = 'all' | 'pending' | 'approved' | 'rejected'
type CategoryFilter = 'all' | 'entity' | 'relation' | 'event'

function confidenceColor(c: number): string {
  if (c >= 0.9) return 'text-green-600 bg-green-50'
  if (c >= 0.6) return 'text-amber-600 bg-amber-50'
  return 'text-red-600 bg-red-50'
}

function confidenceBarColor(c: number): string {
  if (c >= 0.9) return 'bg-green-500'
  if (c >= 0.6) return 'bg-amber-500'
  return 'bg-red-500'
}

function ProposalSummary({ proposal }: { proposal: KGProposal }) {
  const { category, data } = proposal
  if (category === 'entity') {
    return (
      <span className="text-slate-700 font-medium">
        {data.label ? `[${data.label}] ` : ''}{data.name ?? '—'}
      </span>
    )
  }
  if (category === 'relation') {
    return (
      <span className="text-slate-700 font-medium">
        {data.source ?? '?'}
        <span className="text-slate-400 mx-1">→</span>
        {data.relation ?? '?'}
        <span className="text-slate-400 mx-1">→</span>
        {data.target ?? '?'}
      </span>
    )
  }
  // event
  return (
    <span className="text-slate-700 font-medium">
      {data.name ?? data.label ?? '—'}
    </span>
  )
}

export function KGPanel() {
  const { projectId, selectedChapterId } = useWorkspace()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all')
  const [selectedIndex, setSelectedIndex] = useState<number>(0)
  const [error, setError] = useState('')

  // Build query string for status filter
  const statusParam =
    statusFilter === 'pending'
      ? 'pending'
      : statusFilter === 'approved'
      ? 'approved'
      : statusFilter === 'rejected'
      ? 'rejected'
      : undefined

  const queryKey = ['kg-proposals', projectId, statusFilter, categoryFilter]

  const { data: proposals, isLoading } = useQuery({
    queryKey,
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('project_id', String(projectId))
      if (statusParam) params.set('status', statusParam)
      if (categoryFilter !== 'all') params.set('category', categoryFilter)
      return apiFetch<KGProposal[]>(`/api/kg/proposals?${params.toString()}`)
    },
    enabled: !!projectId,
  })

  const extractMutation = useMutation({
    mutationFn: () =>
      apiFetch('/api/kg/extract', {
        method: 'POST',
        body: JSON.stringify({ chapter_id: selectedChapterId, project_id: projectId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kg-proposals', projectId] })
      setError('')
    },
    onError: (e) => setError(e instanceof Error ? e.message : '抽取失败'),
  })

  const approveMutation = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/api/kg/proposals/${id}/approve`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kg-proposals', projectId] }),
    onError: (e) => setError(e instanceof Error ? e.message : '操作失败'),
  })

  const rejectMutation = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/api/kg/proposals/${id}/reject`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kg-proposals', projectId] }),
    onError: (e) => setError(e instanceof Error ? e.message : '操作失败'),
  })

  const bulkApproveMutation = useMutation({
    mutationFn: (ids: number[]) =>
      apiFetch('/api/kg/proposals/bulk-approve', {
        method: 'POST',
        body: JSON.stringify({ ids }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kg-proposals', projectId] }),
    onError: (e) => setError(e instanceof Error ? e.message : '批量操作失败'),
  })

  const bulkRejectMutation = useMutation({
    mutationFn: (ids: number[]) =>
      apiFetch('/api/kg/proposals/bulk-reject', {
        method: 'POST',
        body: JSON.stringify({ ids }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kg-proposals', projectId] }),
    onError: (e) => setError(e instanceof Error ? e.message : '批量操作失败'),
  })

  const list = proposals ?? []
  const pendingIds = list.filter((p) => p.status === 'pending').map((p) => p.id)

  // Stats counts from all proposals irrespective of filter (use current list as approximation)
  const stats = {
    pending: list.filter((p) => p.status === 'pending').length,
    approved: list.filter((p) => p.status === 'auto_approved' || p.status === 'user_approved').length,
    rejected: list.filter((p) => p.status === 'rejected').length,
  }

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't hijack shortcuts when user is typing in an input
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

      const focused = list[selectedIndex]
      if (!focused) return

      if (e.key === 'a' || e.key === 'A') {
        if (focused.status === 'pending') approveMutation.mutate(focused.id)
      } else if (e.key === 'r' || e.key === 'R') {
        if (focused.status === 'pending') rejectMutation.mutate(focused.id)
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault()
        setSelectedIndex((i) => Math.min(i + 1, list.length - 1))
      } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault()
        setSelectedIndex((i) => Math.max(i - 1, 0))
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [list, selectedIndex, approveMutation, rejectMutation])

  // Reset selection index when list changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [statusFilter, categoryFilter, projectId])

  if (!projectId) return null

  const anyMutating =
    approveMutation.isPending ||
    rejectMutation.isPending ||
    bulkApproveMutation.isPending ||
    bulkRejectMutation.isPending

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{error}</div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-600">KG 审阅</span>
        <button
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded
            hover:bg-blue-700 disabled:opacity-50 cursor-pointer transition-colors"
          disabled={!selectedChapterId || extractMutation.isPending}
          onClick={() => extractMutation.mutate()}
        >
          {extractMutation.isPending ? '抽取中...' : '抽取 KG'}
        </button>
      </div>

      {/* Stats bar */}
      <div className="flex gap-2 text-[10px] text-slate-500">
        <span className="text-amber-600 font-medium">{stats.pending} 待审阅</span>
        <span>/</span>
        <span className="text-green-600 font-medium">{stats.approved} 已通过</span>
        <span>/</span>
        <span className="text-slate-400">{stats.rejected} 已拒绝</span>
      </div>

      {/* Status filter tabs */}
      <div className="flex border-b border-slate-100">
        {(['all', 'pending', 'approved', 'rejected'] as const).map((s) => (
          <button
            key={s}
            className={`flex-1 py-1 text-[10px] font-medium transition-colors cursor-pointer ${
              statusFilter === s
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-slate-400 hover:text-slate-600'
            }`}
            onClick={() => setStatusFilter(s)}
          >
            {s === 'all' ? '全部' : s === 'pending' ? '待审阅' : s === 'approved' ? '已通过' : '已拒绝'}
          </button>
        ))}
      </div>

      {/* Category filter pills */}
      <div className="flex flex-wrap gap-1">
        {(['all', 'entity', 'relation', 'event'] as const).map((c) => (
          <button
            key={c}
            className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors cursor-pointer ${
              categoryFilter === c
                ? 'border-blue-400 bg-blue-50 text-blue-600'
                : 'border-slate-200 text-slate-500 hover:border-slate-300'
            }`}
            onClick={() => setCategoryFilter(c)}
          >
            {c === 'all' ? '全部' : CATEGORY_LABELS[c]}
          </button>
        ))}
      </div>

      {/* Bulk actions — only show when there are pending items */}
      {pendingIds.length > 0 && (
        <div className="flex gap-2">
          <button
            className="flex-1 text-[10px] px-2 py-1 bg-green-600 text-white rounded
              hover:bg-green-700 disabled:opacity-50 cursor-pointer transition-colors"
            disabled={anyMutating}
            onClick={() => bulkApproveMutation.mutate(pendingIds)}
          >
            {bulkApproveMutation.isPending ? '处理中...' : `全部通过 (${pendingIds.length})`}
          </button>
          <button
            className="flex-1 text-[10px] px-2 py-1 border border-slate-300 text-slate-600 rounded
              hover:bg-slate-50 disabled:opacity-50 cursor-pointer transition-colors"
            disabled={anyMutating}
            onClick={() => bulkRejectMutation.mutate(pendingIds)}
          >
            {bulkRejectMutation.isPending ? '处理中...' : '全部拒绝'}
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-6">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Proposal list */}
      {!isLoading && (
        <div className="space-y-2">
          {list.map((proposal, idx) => (
            <div
              key={proposal.id}
              className={`border rounded p-2 space-y-1.5 cursor-pointer transition-colors ${
                idx === selectedIndex
                  ? 'border-blue-300 bg-blue-50/40'
                  : 'border-slate-100 bg-white hover:border-slate-200 hover:bg-slate-50/50'
              }`}
              onClick={() => setSelectedIndex(idx)}
            >
              {/* Top row: category badge + status badge */}
              <div className="flex items-center gap-1.5">
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    CATEGORY_COLORS[proposal.category] ?? 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {CATEGORY_LABELS[proposal.category] ?? proposal.category}
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] ${
                    STATUS_COLORS[proposal.status] ?? 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {STATUS_LABELS[proposal.status] ?? proposal.status}
                </span>
                {/* Confidence badge */}
                <span
                  className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-medium ${
                    confidenceColor(proposal.confidence)
                  }`}
                >
                  {Math.round(proposal.confidence * 100)}%
                </span>
              </div>

              {/* Confidence bar */}
              <div className="h-0.5 bg-slate-100 rounded">
                <div
                  className={`h-0.5 rounded transition-all ${confidenceBarColor(proposal.confidence)}`}
                  style={{ width: `${Math.round(proposal.confidence * 100)}%` }}
                />
              </div>

              {/* Proposal summary */}
              <div className="text-xs">
                <ProposalSummary proposal={proposal} />
              </div>

              {/* Properties (entity only) */}
              {proposal.category === 'entity' &&
                proposal.data.properties &&
                Object.keys(proposal.data.properties).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(proposal.data.properties).map(([k, v]) => (
                      <span key={k} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                )}

              {/* Evidence text */}
              {proposal.evidence_text && (
                <blockquote className="text-[10px] text-slate-400 italic border-l-2 border-slate-200 pl-2 leading-relaxed line-clamp-2">
                  {proposal.evidence_text}
                </blockquote>
              )}

              {/* Approve / Reject buttons for pending */}
              {proposal.status === 'pending' && (
                <div className="flex gap-1.5 pt-0.5">
                  <button
                    className="flex-1 text-[10px] py-1 bg-green-600 text-white rounded
                      hover:bg-green-700 disabled:opacity-50 cursor-pointer transition-colors"
                    disabled={anyMutating}
                    onClick={(e) => {
                      e.stopPropagation()
                      approveMutation.mutate(proposal.id)
                    }}
                  >
                    通过 (A)
                  </button>
                  <button
                    className="flex-1 text-[10px] py-1 border border-slate-300 text-slate-600 rounded
                      hover:bg-slate-100 disabled:opacity-50 cursor-pointer transition-colors"
                    disabled={anyMutating}
                    onClick={(e) => {
                      e.stopPropagation()
                      rejectMutation.mutate(proposal.id)
                    }}
                  >
                    拒绝 (R)
                  </button>
                </div>
              )}
            </div>
          ))}

          {list.length === 0 && (
            <div className="text-center text-xs text-slate-400 py-6">
              暂无提案
            </div>
          )}
        </div>
      )}
    </div>
  )
}
