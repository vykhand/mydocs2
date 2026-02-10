<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Upload, FileText, Search, Briefcase, Settings } from 'lucide-vue-next'

defineProps<{
  collapsed: boolean
}>()

const route = useRoute()

const navItems = [
  { path: '/upload', label: 'Upload', icon: Upload },
  { path: '/documents', label: 'Documents', icon: FileText },
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
    class="shrink-0 border-r flex flex-col py-3 transition-all duration-200 overflow-hidden"
    :style="{
      width: collapsed ? 'var(--width-sidebar-collapsed)' : 'var(--width-sidebar)',
      backgroundColor: 'var(--color-bg-secondary)',
      borderColor: 'var(--color-border)',
    }"
  >
    <router-link
      v-for="item in navItems"
      :key="item.path"
      :to="item.path"
      class="flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg transition-colors text-sm font-medium"
      :style="{
        color: isActive(item.path) ? 'var(--color-accent)' : 'var(--color-text-secondary)',
        backgroundColor: isActive(item.path) ? 'var(--color-bg-tertiary)' : 'transparent',
      }"
      :title="collapsed ? item.label : undefined"
    >
      <component :is="item.icon" :size="20" class="shrink-0" />
      <span v-if="!collapsed" class="whitespace-nowrap">{{ item.label }}</span>
    </router-link>
  </nav>
</template>
