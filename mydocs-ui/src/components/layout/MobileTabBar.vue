<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { FileText, Briefcase, MoreHorizontal } from 'lucide-vue-next'
import { ref } from 'vue'

const route = useRoute()
const appStore = useAppStore()
const showMore = ref(false)

const tabs = [
  { path: '/', label: 'Documents', icon: FileText, tab: 'documents' as const },
  { path: '/cases', label: 'Cases', icon: Briefcase, tab: 'cases' as const },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/' || route.path.startsWith('/doc')
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
    <button
      @click="showMore = !showMore"
      class="flex flex-col items-center gap-0.5 px-2 py-1 rounded-md text-xs"
      style="color: var(--color-text-secondary);"
    >
      <MoreHorizontal :size="20" />
      <span>More</span>
    </button>
  </nav>

  <!-- More menu overlay -->
  <Teleport to="body">
    <div v-if="showMore" class="fixed inset-0 z-50 flex items-end">
      <div class="absolute inset-0 bg-black/50" @click="showMore = false" />
      <div
        class="relative z-10 w-full rounded-t-xl p-4 space-y-2"
        style="background-color: var(--color-bg-primary);"
      >
        <router-link
          to="/upload"
          @click="showMore = false"
          class="block px-4 py-3 rounded-lg text-sm font-medium"
          style="color: var(--color-text-primary); background-color: var(--color-bg-secondary);"
        >
          Upload
        </router-link>
        <router-link
          to="/settings"
          @click="showMore = false"
          class="block px-4 py-3 rounded-lg text-sm font-medium"
          style="color: var(--color-text-primary); background-color: var(--color-bg-secondary);"
        >
          Settings
        </router-link>
        <button
          @click="showMore = false"
          class="w-full px-4 py-3 rounded-lg text-sm font-medium text-center"
          style="color: var(--color-text-secondary);"
        >
          Cancel
        </button>
      </div>
    </div>
  </Teleport>
</template>
