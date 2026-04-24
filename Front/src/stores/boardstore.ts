// front/board/boardStore.ts
// WP_Capstone — P-07 커뮤니티 게시판 Pinia 스토어

import { defineStore } from 'pinia'
import dbapi from '@/api/dbapi'

// ─── 타입 정의 ──────────────────────────────────────────────

export interface PostSummary {
  id: number
  ticker: string
  author_id: number
  title: string
  views: number
  likes: number
  liked: boolean
  comment_count: number
  created_at: string
}

export interface Comment {
  id: number
  author_id: number
  content: string
  created_at: string
}

export interface PostDetail extends PostSummary {
  content: string
  updated_at: string
  comments: Comment[]
}

export interface PostsState {
  /** 현재 조회 중인 ticker */
  currentTicker: string | null
  /** 게시글 목록 */
  posts: PostSummary[]
  /** 전체 글 수 */
  total: number
  /** 현재 페이지 */
  page: number
  pageSize: number
  /** 게시글 상세 캐시 (id → PostDetail) */
  postCache: Record<number, PostDetail>
  loading: boolean
  error: string | null
}

// ─── 스토어 ─────────────────────────────────────────────────

export const useBoardStore = defineStore('board', {
  state: (): PostsState => ({
    currentTicker: null,
    posts: [],
    total: 0,
    page: 1,
    pageSize: 20,
    postCache: {},
    loading: false,
    error: null,
  }),

  getters: {
    totalPages: (s) => Math.max(1, Math.ceil(s.total / s.pageSize)),
  },

  actions: {
    // ── 게시글 목록 조회 ────────────────────────────────────
    async fetchPosts(ticker: string, page = 1) {
      this.loading = true
      this.error = null
      try {
        const { data } = await dbapi.get(`/api/v1/board/posts/${ticker}`, {
          params: { page, page_size: this.pageSize },
        })
        this.currentTicker = ticker
        this.posts = data.items
        this.total = data.total
        this.page = data.page
      } catch (e: any) {
        this.error = e?.response?.data?.detail ?? '게시글 목록을 불러오지 못했습니다.'
        throw e
      } finally {
        this.loading = false
      }
    },

    // ── 게시글 상세 조회 (views +1) ────────────────────────
    async fetchPostDetail(postId: number): Promise<PostDetail> {
      this.loading = true
      this.error = null
      try {
        const { data } = await dbapi.get(`/api/v1/board/posts/detail/${postId}`)
        this.postCache[postId] = data
        return data
      } catch (e: any) {
        this.error = e?.response?.data?.detail ?? '게시글을 불러오지 못했습니다.'
        throw e
      } finally {
        this.loading = false
      }
    },

    // ── 게시글 작성 ────────────────────────────────────────
    async createPost(ticker: string, title: string, content: string): Promise<PostDetail> {
      const { data } = await dbapi.post('/api/v1/board/posts', { ticker, title, content })
      // 목록 맨 앞에 낙관적 삽입
      this.posts.unshift({ ...data, comment_count: 0, liked: false })
      this.total += 1
      return data
    },

    // ── 게시글 삭제 ────────────────────────────────────────
    async deletePost(postId: number) {
      await dbapi.delete(`/api/v1/board/posts/${postId}`)
      this.posts = this.posts.filter((p) => p.id !== postId)
      this.total = Math.max(0, this.total - 1)
      delete this.postCache[postId]
    },

    // ── 댓글 작성 ─────────────────────────────────────────
    async createComment(postId: number, content: string): Promise<Comment> {
      const { data } = await dbapi.post('/api/v1/board/comments', { post_id: postId, content })
      // 캐시된 상세에 바로 반영
      if (this.postCache[postId]) {
        this.postCache[postId].comments.push(data)
      }
      // 목록의 댓글 수 +1
      const target = this.posts.find((p) => p.id === postId)
      if (target) target.comment_count += 1
      return data
    },

    // ── 좋아요 토글 ────────────────────────────────────────
    async toggleLike(postId: number) {
      // 낙관적 업데이트
      const listItem = this.posts.find((p) => p.id === postId)
      const cacheItem = this.postCache[postId]

      const wasLiked = listItem?.liked ?? cacheItem?.liked ?? false
      const delta = wasLiked ? -1 : 1

      if (listItem) {
        listItem.liked = !wasLiked
        listItem.likes += delta
      }
      if (cacheItem) {
        cacheItem.liked = !wasLiked
        cacheItem.likes += delta
      }

      try {
        const { data } = await dbapi.post(`/api/v1/board/posts/${postId}/like`)
        // 서버 응답으로 동기화
        if (listItem) {
          listItem.liked = data.liked
          listItem.likes = data.likes
        }
        if (cacheItem) {
          cacheItem.liked = data.liked
          cacheItem.likes = data.likes
        }
        return data
      } catch (e) {
        // 롤백
        if (listItem) {
          listItem.liked = wasLiked
          listItem.likes -= delta
        }
        if (cacheItem) {
          cacheItem.liked = wasLiked
          cacheItem.likes -= delta
        }
        throw e
      }
    },

    // ── 상태 초기화 ────────────────────────────────────────
    reset() {
      this.currentTicker = null
      this.posts = []
      this.total = 0
      this.page = 1
      this.postCache = {}
      this.error = null
    },
  },
})