import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import Toast, { type PluginOptions } from 'vue-toastification'
import 'vue-toastification/dist/index.css'

import { useToast } from 'vue-toastification'

import App from './App.vue'
import router from './router'
import './assets/main.css'
import { useAuth } from './auth/useAuth'

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

const toastOptions: PluginOptions = {
  timeout: 4000,
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  showCloseButtonOnHover: true,
}

async function bootstrap() {
  const { initialize } = useAuth()
  await initialize()

  const app = createApp(App)
  app.use(pinia)
  app.use(router)
  app.use(Toast, toastOptions)

  app.config.errorHandler = (err) => {
    console.error('Unhandled error:', err)
    const toast = useToast()
    const message = err instanceof Error ? err.message : 'An unexpected error occurred'
    toast.error(message)
  }

  app.mount('#app')
}

bootstrap()
