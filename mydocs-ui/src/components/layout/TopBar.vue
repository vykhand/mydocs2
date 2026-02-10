<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { useResponsive } from '@/composables/useResponsive'
import ModeToggle from '@/components/common/ModeToggle.vue'
import { Sun, Moon, Monitor, PanelLeftClose, PanelLeft } from 'lucide-vue-next'

const appStore = useAppStore()
const { isMobile } = useResponsive()

function cycleTheme() {
  const order = ['light', 'dark', 'system'] as const
  const idx = order.indexOf(appStore.theme)
  appStore.setTheme(order[(idx + 1) % 3])
}
</script>

<template>
  <header
    class="h-14 flex items-center justify-between px-4 border-b shrink-0"
    style="background-color: var(--color-bg-secondary); border-color: var(--color-border);"
  >
    <div class="flex items-center gap-3">
      <button
        v-if="!isMobile"
        @click="appStore.toggleSidebar()"
        class="p-1.5 rounded-md hover:opacity-80 transition-opacity"
        style="color: var(--color-text-secondary);"
        aria-label="Toggle sidebar"
      >
        <PanelLeftClose v-if="!appStore.sidebarCollapsed" :size="20" />
        <PanelLeft v-else :size="20" />
      </button>
      <router-link to="/" class="flex items-center gap-2 font-semibold text-lg" style="color: var(--color-text-primary);">
        <span>mydocs</span>
      </router-link>
    </div>
    <div class="flex items-center gap-3">
      <ModeToggle />
      <button
        @click="cycleTheme"
        class="p-2 rounded-md hover:opacity-80 transition-opacity"
        style="color: var(--color-text-secondary);"
        :aria-label="`Theme: ${appStore.theme}`"
      >
        <Sun v-if="appStore.theme === 'light'" :size="18" />
        <Moon v-else-if="appStore.theme === 'dark'" :size="18" />
        <Monitor v-else :size="18" />
      </button>
    </div>
  </header>
</template>
