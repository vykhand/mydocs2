<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useResponsive } from '@/composables/useResponsive'
import TopBar from './TopBar.vue'
import SidebarNav from './SidebarNav.vue'
import MobileTabBar from './MobileTabBar.vue'
import RightViewerPanel from './RightViewerPanel.vue'

const appStore = useAppStore()
const { isMobile, isTablet, isDesktop, isWide } = useResponsive()

onMounted(() => {
  appStore.applyTheme()
})

const sidebarMode = computed(() => {
  if (isMobile.value) return 'hidden'
  if (isTablet.value) return 'drawer'
  if (isDesktop.value) return 'icon-rail'
  return 'expanded' // isWide
})

const showSidebarDrawer = computed(() => {
  return isTablet.value && !appStore.sidebarCollapsed
})
</script>

<template>
  <div class="h-screen flex flex-col" style="background-color: var(--color-bg-primary); color: var(--color-text-primary);">
    <TopBar />
    <div class="flex flex-1 overflow-hidden">
      <!-- Sidebar: expanded on wide, icon-rail on desktop, drawer on tablet, hidden on mobile -->
      <SidebarNav
        v-if="sidebarMode === 'expanded'"
        :collapsed="false"
      />
      <SidebarNav
        v-else-if="sidebarMode === 'icon-rail'"
        :collapsed="!appStore.sidebarCollapsed ? false : true"
      />

      <!-- Tablet drawer overlay -->
      <Teleport to="body">
        <div v-if="showSidebarDrawer" class="fixed inset-0 z-40 flex">
          <div class="absolute inset-0 bg-black/50" @click="appStore.toggleSidebar()" />
          <div class="relative z-10">
            <SidebarNav :collapsed="false" />
          </div>
        </div>
      </Teleport>

      <!-- Main content (gallery) -->
      <main class="flex-1 overflow-y-auto p-4 md:p-6" style="background-color: var(--color-bg-primary);">
        <slot />
      </main>

      <!-- Right viewer panel -->
      <RightViewerPanel
        v-if="appStore.viewerOpen"
        :class="{
          'w-[420px] shrink-0 border-l': isWide || isDesktop,
          'fixed inset-0 z-50': isTablet || isMobile,
        }"
      />
    </div>
    <MobileTabBar v-if="isMobile" />
  </div>
</template>
