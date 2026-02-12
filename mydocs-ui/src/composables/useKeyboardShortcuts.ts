import { onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'

export function useKeyboardShortcuts() {
  const appStore = useAppStore()

  function handler(e: KeyboardEvent) {
    // Cmd+K / Ctrl+K → focus search bar (handled in TopBar, but also global escape)
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      const input = document.querySelector<HTMLInputElement>('header input[type="text"]')
      input?.focus()
      return
    }

    // "/" → focus search bar (when no input focused)
    if (e.key === '/' && !isInputFocused()) {
      e.preventDefault()
      const input = document.querySelector<HTMLInputElement>('header input[type="text"]')
      input?.focus()
      return
    }

    // Escape → close viewer or modal
    if (e.key === 'Escape') {
      if (appStore.viewerOpen) {
        appStore.closeViewer()
        return
      }
    }
  }

  function isInputFocused(): boolean {
    const el = document.activeElement
    if (!el) return false
    const tag = el.tagName.toLowerCase()
    return tag === 'input' || tag === 'textarea' || tag === 'select' || (el as HTMLElement).isContentEditable
  }

  onMounted(() => {
    document.addEventListener('keydown', handler)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handler)
  })
}
