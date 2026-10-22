import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles.css'
import './gallery.css'
import './themes.css'
import './play.css'
import { dialogDirective } from './utils/dialog'

const app = createApp(App)
app.use(createPinia())
app.directive('dialog', dialogDirective)
app.mount('#app')

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // 注册失败（如非 HTTPS）时不影响正常使用
    })
  })
}
