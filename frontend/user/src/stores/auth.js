import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    circles: [],
    currentCircleId: null,
    loaded: false,
    circleRequest: 0,
  }),
  getters: {
    isAuthenticated: (s) => !!s.user,
    currentCircle: (s) =>
      s.circles.find((c) => c.id === s.currentCircleId) || null,
    isOwner: (s) => {
      const c = s.circles.find((x) => x.id === s.currentCircleId)
      return !!c?.is_owner
    },
    canManage: (s) =>
      !!s.circles.find((c) => c.id === s.currentCircleId)?.can_manage,
  },
  actions: {
    async fetchMe() {
      try {
        const { data } = await api.get('/api/auth/me')
        this.user = data
      } catch {
        this.user = null
      } finally {
        this.loaded = true
      }
    },
    async login(username, password) {
      const { data } = await api.post('/api/auth/login', { username, password })
      this.user = data
      await this.fetchCircles()
    },
    async register(username, password, nickname) {
      const { data } = await api.post('/api/auth/register', {
        username,
        password,
        nickname,
      })
      this.user = data
      await this.fetchCircles()
    },
    async logout() {
      await api.post('/api/auth/logout')
      this.user = null
      this.circles = []
      this.currentCircleId = null
    },
    async fetchCircles() {
      const request = ++this.circleRequest,
        expectedUser = this.user
      const { data } = await api.get('/api/circles')
      if (request !== this.circleRequest || expectedUser !== this.user)
        return this.circles
      this.circles = data
      if (!this.currentCircleId && data.length) {
        this.currentCircleId = data[0].id
      }
      if (
        this.currentCircleId &&
        !data.find((c) => c.id === this.currentCircleId)
      ) {
        this.currentCircleId = data[0]?.id || null
      }
      return data
    },
    setCurrentCircle(id) {
      this.currentCircleId = id
      localStorage.setItem('currentCircleId', String(id || ''))
    },
    restoreCircle() {
      const raw = localStorage.getItem('currentCircleId')
      if (raw) this.currentCircleId = Number(raw) || null
    },
  },
})
