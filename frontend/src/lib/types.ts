export interface Project {
  id: number
  title: string
  description: string
  created_at: string
  updated_at: string
}

export interface Book {
  id: number
  project_id: number
  title: string
  sort_order: number
  created_at: string
}

export interface Chapter {
  id: number
  book_id: number
  title: string
  sort_order: number
  status: string
  created_at: string
}

export interface Scene {
  id: number
  chapter_id: number
  title: string
  sort_order: number
  created_at: string
}

export interface SceneVersion {
  id: number
  scene_id: number
  version: number
  content_md: string
  char_count: number
  created_at: string
  created_by: string
}

export interface SceneTreeNode {
  id: number
  title: string
  sort_order: number
}

export interface ChapterTreeNode {
  id: number
  title: string
  sort_order: number
  status: string
  scenes: SceneTreeNode[]
}

export interface BookTreeNode {
  id: number
  title: string
  sort_order: number
  chapters: ChapterTreeNode[]
}

export interface ProjectTree {
  id: number
  title: string
  books: BookTreeNode[]
}

export interface LoreEntry {
  id: number
  project_id: number
  type: string
  title: string
  aliases: string[]
  content_md: string
  secrets_md: string
  triggers: {
    keywords: string[]
    and_keywords?: string[]
  }
  priority: number
  locked: boolean
  created_at: string
  updated_at: string
}

export type KGCategory = 'entity' | 'relation' | 'event'
export type KGStatus = 'pending' | 'auto_approved' | 'user_approved' | 'rejected'

export interface KGProposal {
  id: number
  project_id: number
  chapter_id: number
  category: KGCategory
  data: {
    label?: string
    name?: string
    properties?: Record<string, string>
    source?: string
    target?: string
    relation?: string
  }
  confidence: number
  status: KGStatus
  evidence_text: string
  evidence_location: string
  reviewed_at: string | null
  created_at: string
}

export type ConflictSeverity = 'high' | 'medium' | 'low'
export type ConflictType = 'character_status' | 'timeline' | 'possession' | 'plot_thread' | 'repetition'

export interface ConsistencyResult {
  type: ConflictType
  severity: ConflictSeverity
  confidence: number
  source: string
  message: string
  evidence: string[]
  evidence_locations: string[]
  suggest_fix: string
}

export interface KGNode {
  id: number
  project_id: number
  label: string
  name: string
  properties: Record<string, string>
  created_at: string
}

export interface KGEdge {
  id: number
  project_id: number
  source_node_id: number
  target_node_id: number
  relation: string
  properties: Record<string, string>
}
