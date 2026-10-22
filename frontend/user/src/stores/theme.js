import { defineStore } from 'pinia'
import api from '../api'

/* 预设主题清单：css 类名与 themes.css 中的 html[data-theme='...'] 对应 */
export const THEME_PRESETS = [
  { key: 'default', label: '纸墨', desc: '默认暖纸手账', dots: ['#f5f6f4', '#ffffff', '#ad4737', '#3c6255'] },
  { key: 'night', label: '暗夜', desc: '深夜翻相册', dots: ['#161a19', '#212726', '#d9815f', '#7fb3a0'] },
  { key: 'sakura', label: '樱花', desc: '春日限定粉', dots: ['#fbf3f4', '#fffafa', '#e0809a', '#a5516c'] },
  { key: 'ocean', label: '海盐', desc: '清爽海风味', dots: ['#edf4f5', '#fcfeff', '#e07a54', '#2f6b7a'] },
  { key: 'pine', label: '松烟', desc: '山间墨绿调', dots: ['#eef2ec', '#fafcf8', '#c96b4a', '#2e5346'] },
  { key: 'wheat', label: '金穗', desc: '秋收暖阳色', dots: ['#faf3e2', '#fffdf4', '#d9903f', '#8a6d2f'] },
]

/* 自定义配色可调变量；其余变量由 color-mix 推导 */
export const CUSTOM_FIELDS = [
  { key: '--paper', label: '页面底色', fallback: '#f5f6f4' },
  { key: '--surface', label: '卡片底色', fallback: '#ffffff' },
  { key: '--ink', label: '文字颜色', fallback: '#242927' },
  { key: '--terracotta', label: '强调色', fallback: '#ad4737' },
  { key: '--pine', label: '辅助色', fallback: '#3c6255' },
]
const CUSTOM_KEYS = CUSTOM_FIELDS.map((f) => f.key)
const DERIVED_KEYS = ['--muted', '--line', '--terracotta-dark']
const STORAGE_KEY = 'sgj-theme'

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data || typeof data.preset !== 'string') return null
    return { preset: data.preset, custom: data.custom || null }
  } catch {
    return null
  }
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    preset: 'default',
    custom: null,
  }),
  actions: {
    /* 启动时先从 localStorage 应用，避免主题闪烁 */
    boot() {
      const cached = readStorage()
      if (cached) {
        this.preset = cached.preset
        this.custom = cached.custom
      }
      this.apply()
    },
    apply() {
      const el = document.documentElement
      for (const key of [...CUSTOM_KEYS, ...DERIVED_KEYS]) {
        el.style.removeProperty(key)
      }
      if (this.preset === 'custom' && this.custom) {
        el.dataset.theme = 'custom'
        for (const key of CUSTOM_KEYS) {
          const value = this.custom[key]
          if (value) el.style.setProperty(key, value)
        }
        /* 由用户选的颜色推导辅助色，保证对比度不至于失控 */
        el.style.setProperty('--muted', 'color-mix(in srgb, var(--ink) 55%, var(--paper))')
        el.style.setProperty('--line', 'color-mix(in srgb, var(--ink) 16%, var(--paper))')
        el.style.setProperty('--terracotta-dark', 'color-mix(in srgb, var(--terracotta) 82%, #000)')
      } else if (this.preset && this.preset !== 'default') {
        el.dataset.theme = this.preset
      } else {
        el.removeAttribute('data-theme')
      }
    },
    /* 登录后按账号同步服务端保存的偏好；服务端无记录则保留本地选择 */
    syncFromUser(user) {
      if (!user?.theme_preference) {
        this.apply()
        return
      }
      try {
        const data = JSON.parse(user.theme_preference)
        if (data && typeof data.preset === 'string') {
          this.preset = data.preset
          this.custom = data.custom || null
        }
      } catch {
        /* 服务端内容异常时沿用本地 */
      }
      this.apply()
      this.cacheLocal()
    },
    cacheLocal() {
      try {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ preset: this.preset, custom: this.custom }),
        )
      } catch {
        /* 隐私模式等场景忽略 */
      }
    },
    /* 应用并持久化：本地缓存 + 服务端（已登录时） */
    async persist() {
      this.apply()
      this.cacheLocal()
      try {
        await api.put('/api/auth/theme', {
          preset: this.preset,
          custom: this.custom,
        })
      } catch {
        /* 保存失败不阻断本地生效 */
      }
    },
    async selectPreset(key) {
      this.preset = key
      await this.persist()
    },
    async saveCustom(colors) {
      const custom = {}
      for (const key of CUSTOM_KEYS) {
        if (colors[key]) custom[key] = colors[key]
      }
      if (!Object.keys(custom).length) return
      this.preset = 'custom'
      this.custom = custom
      await this.persist()
    },
  },
})
