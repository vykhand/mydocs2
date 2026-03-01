<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useResponsive } from '@/composables/useResponsive'
import ModeToggle from '@/components/common/ModeToggle.vue'
import { useAuth } from '@/auth/useAuth'
import { Sun, Moon, Monitor, PanelLeftClose, PanelLeft, Search, Upload, Settings, LogOut } from 'lucide-vue-next'

const appStore = useAppStore()
const { userName, logout } = useAuth()
const router = useRouter()
const route = useRoute()
const { isMobile } = useResponsive()

const searchInput = ref<HTMLInputElement | null>(null)
const searchQuery = ref((route.query.q as string) || '')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

// Sync search bar from URL
watch(() => route.query.q, (q) => {
  searchQuery.value = (q as string) || ''
})

// Debounced search → URL
function onSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    const query = { ...route.query }
    if (searchQuery.value) {
      query.q = searchQuery.value
    } else {
      delete query.q
    }
    router.replace({ path: route.path === '/cases' || route.path.startsWith('/cases/') ? route.path : '/', query })
  }, 300)
}

// Cmd+K / Ctrl+K keyboard shortcut
function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    searchInput.value?.focus()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

function cycleTheme() {
  const order = ['light', 'dark', 'system'] as const
  const idx = order.indexOf(appStore.theme)
  appStore.setTheme(order[(idx + 1) % 3])
}
</script>

<template>
  <header
    class="shrink-0 flex items-center justify-between px-4 border-b gap-3"
    style="height: var(--height-topbar); background-color: var(--color-bg-secondary); border-color: var(--color-border);"
  >
    <!-- Left: sidebar toggle + logo -->
    <div class="flex items-center gap-3 shrink-0">
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
      <router-link
        to="/cases"
        class="text-sm font-medium px-2 py-1 rounded hover:opacity-80 transition-opacity"
        :style="{ color: $route.path.startsWith('/cases') ? 'var(--color-accent)' : 'var(--color-text-secondary)' }"
      >
        Cases
      </router-link>
    </div>

    <!-- Center: search bar (hidden on mobile) -->
    <div v-if="!isMobile" class="flex-1 max-w-xl mx-4">
      <div
        class="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
        style="background-color: var(--color-bg-tertiary); border-color: var(--color-border);"
      >
        <Search :size="16" style="color: var(--color-text-secondary);" class="shrink-0" />
        <input
          ref="searchInput"
          v-model="searchQuery"
          @input="onSearchInput"
          type="text"
          placeholder="Search documents... (Cmd+K)"
          class="flex-1 bg-transparent outline-none text-sm"
          style="color: var(--color-text-primary);"
        />
        <kbd
          class="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium border"
          style="border-color: var(--color-border); color: var(--color-text-secondary);"
        >
          <span>&#8984;K</span>
        </kbd>
      </div>
    </div>

    <!-- Right: actions -->
    <div class="flex items-center gap-2 shrink-0">
      <button
        @click="router.push('/upload')"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white"
        style="background-color: var(--color-accent);"
      >
        <Upload :size="16" />
        <span class="hidden sm:inline">Upload</span>
      </button>
      <button
        @click="router.push('/settings')"
        class="p-2 rounded-md hover:opacity-80 transition-opacity"
        style="color: var(--color-text-secondary);"
        aria-label="Settings"
      >
        <Settings :size="18" />
      </button>
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
      <!-- User info & logout -->
      <span
        v-if="userName"
        class="hidden md:inline text-xs truncate max-w-[120px]"
        style="color: var(--color-text-secondary);"
        :title="userName"
      >{{ userName }}</span>
      <button
        @click="logout"
        class="p-2 rounded-md hover:opacity-80 transition-opacity"
        style="color: var(--color-text-secondary);"
        aria-label="Sign out"
        title="Sign out"
      >
        <LogOut :size="18" />
      </button>
    </div>
  </header>
</template>
