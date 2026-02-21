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
  keywords: string[]
  priority: number
  locked: boolean
  created_at: string
  updated_at: string
}
