// @ts-nocheck
// front/board/boardStore.ts
// WP_Capstone ??P-07 而ㅻ??덊떚 寃뚯떆??Pinia ?ㅽ넗??

import { defineStore } from 'pinia'
import dbapi from '@/api/dbapi'

// ??? ????뺤쓽 ??????????????????????????????????????????????

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
  /** ?꾩옱 議고쉶 以묒씤 ticker */
  currentTicker: string | null
  /** 寃뚯떆湲 紐⑸줉 */
  posts: PostSummary[]
  /** ?꾩껜 湲 ??*/
  total: number
  /** ?꾩옱 ?섏씠吏 */
  page: number
  pageSize: number
  /** 寃뚯떆湲 ?곸꽭 罹먯떆 (id ??PostDetail) */
  postCache: Record<number, PostDetail>
  loading: boolean
  error: string | null
}

// ??? ?ㅽ넗???????????????????????????????????????????????????

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
    // ?? 寃뚯떆湲 紐⑸줉 議고쉶 ????????????????????????????????????
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
        this.error = e?.response?.data?.detail ?? '寃뚯떆湲 紐⑸줉??遺덈윭?ㅼ? 紐삵뻽?듬땲??'
        throw e
      } finally {
        this.loading = false
      }
    },

    // ?? 寃뚯떆湲 ?곸꽭 議고쉶 (views +1) ????????????????????????
    async fetchPostDetail(postId: number): Promise<PostDetail> {
      this.loading = true
      this.error = null
      try {
        const { data } = await dbapi.get(`/api/v1/board/posts/detail/${postId}`)
        this.postCache[postId] = data
        return data
      } catch (e: any) {
        this.error = e?.response?.data?.detail ?? '寃뚯떆湲??遺덈윭?ㅼ? 紐삵뻽?듬땲??'
        throw e
      } finally {
        this.loading = false
      }
    },

    // ?? 寃뚯떆湲 ?묒꽦 ????????????????????????????????????????
    async createPost(ticker: string, title: string, content: string): Promise<PostDetail> {
      const { data } = await dbapi.post('/api/v1/board/posts', { ticker, title, content })
      // 紐⑸줉 留??욎뿉 ?숆????쎌엯
      this.posts.unshift({ ...data, comment_count: 0, liked: false })
      this.total += 1
      return data
    },

    // ?? 寃뚯떆湲 ??젣 ????????????????????????????????????????
    async deletePost(postId: number) {
      await dbapi.delete(`/api/v1/board/posts/${postId}`)
      this.posts = this.posts.filter((p) => p.id !== postId)
      this.total = Math.max(0, this.total - 1)
      delete this.postCache[postId]
    },

    // ?? ?볤? ?묒꽦 ?????????????????????????????????????????
    async createComment(postId: number, content: string): Promise<Comment> {
      const { data } = await dbapi.post('/api/v1/board/comments', { post_id: postId, content })
      // 罹먯떆???곸꽭??諛붾줈 諛섏쁺
      if (this.postCache[postId]) {
        this.postCache[postId].comments.push(data)
      }
      // 紐⑸줉???볤? ??+1
      const target = this.posts.find((p) => p.id === postId)
      if (target) target.comment_count += 1
      return data
    },

    // ?? 醫뗭븘???좉? ????????????????????????????????????????
    async toggleLike(postId: number) {
      // ?숆????낅뜲?댄듃
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
        // ?쒕쾭 ?묐떟?쇰줈 ?숆린??
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
        // 濡ㅻ갚
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

    // ?? ?곹깭 珥덇린??????????????????????????????????????????
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