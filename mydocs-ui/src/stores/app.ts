import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type AppMode = 'simple' | 'advanced'
export type ThemeMode = 'light' | 'dark' | 'system'

export const useAppStore = defineStore('app', () => {
  const mode = ref<AppMode>('simple')
  const theme = ref<ThemeMode>('system')
  const sidebarCollapsed = ref(false)

  function toggleMode() {
    mode.value = mode.value === 'simple' ? 'advanced' : 'simple'
  }

  function setTheme(t: ThemeMode) {
    theme.value = t
    applyTheme()
  }

  function applyTheme() {
    const root = document.documentElement
    if (theme.value === 'dark' || (theme.value === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // Watch for system theme changes
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (theme.value === 'system') applyTheme()
    })
  }

  return { mode, theme, sidebarCollapsed, toggleMode, setTheme, applyTheme, toggleSidebar }
}, {
  persist: true,
})
