<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useResponsive } from '@/composables/useResponsive'
import TopBar from './TopBar.vue'
import SidebarNav from './SidebarNav.vue'
import MobileTabBar from './MobileTabBar.vue'

const appStore = useAppStore()
const { isMobile, isTablet } = useResponsive()

onMounted(() => {
  appStore.applyTheme()
})
</script>

<template>
  <div class="h-screen flex flex-col" style="background-color: var(--color-bg-primary); color: var(--color-text-primary);">
    <TopBar />
    <div class="flex flex-1 overflow-hidden">
      <SidebarNav
        v-if="!isMobile"
        :collapsed="isTablet || appStore.sidebarCollapsed"
      />
      <main class="flex-1 overflow-y-auto p-4 md:p-6" style="background-color: var(--color-bg-primary);">
        <slot />
      </main>
    </div>
    <MobileTabBar v-if="isMobile" />
  </div>
</template>
