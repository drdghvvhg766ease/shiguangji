import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 鐙珛绠＄悊鍙帮細涓庣敤鎴风鍓嶇鍒嗙锛屼粎鍏辩敤鍚庣 API
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})

