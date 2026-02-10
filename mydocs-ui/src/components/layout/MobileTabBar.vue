<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Upload, FileText, Search, Briefcase, Settings } from 'lucide-vue-next'

const route = useRoute()

const tabs = [
  { path: '/upload', label: 'Upload', icon: Upload },
  { path: '/documents', label: 'Docs', icon: FileText },
  { path: '/search', label: 'Search', icon: Search },
  { path: '/cases', label: 'Cases', icon: Briefcase },
  { path: '/settings', label: 'Settings', icon: Settings },
]

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<template>
  <nav
    class="flex items-center justify-around border-t py-1.5 shrink-0"
    style="background-color: var(--color-bg-secondary); border-color: var(--color-border);"
  >
    <router-link
      v-for="tab in tabs"
      :key="tab.path"
      :to="tab.path"
      class="flex flex-col items-center gap-0.5 px-2 py-1 rounded-md text-xs transition-colors"
      :style="{ color: isActive(tab.path) ? 'var(--color-accent)' : 'var(--color-text-secondary)' }"
    >
      <component :is="tab.icon" :size="20" />
      <span>{{ tab.label }}</span>
    </router-link>
  </nav>
</template>
