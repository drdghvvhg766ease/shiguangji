import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles.css'
import './gallery.css'
import { dialogDirective } from './utils/dialog'

const app = createApp(App)
app.use(createPinia())
app.directive('dialog', dialogDirective)
app.mount('#app')
