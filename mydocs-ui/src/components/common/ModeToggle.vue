<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
</script>

<template>
  <div
    class="inline-flex rounded-lg p-0.5 text-xs font-medium"
    style="background-color: var(--color-bg-tertiary);"
  >
    <button
      @click="appStore.mode = 'simple'"
      class="px-3 py-1.5 rounded-md transition-all"
      :style="{
        backgroundColor: appStore.mode === 'simple' ? 'var(--color-bg-primary)' : 'transparent',
        color: appStore.mode === 'simple' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
        boxShadow: appStore.mode === 'simple' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
      }"
    >
      Simple
    </button>
    <button
      @click="appStore.mode = 'advanced'"
      class="px-3 py-1.5 rounded-md transition-all"
      :style="{
        backgroundColor: appStore.mode === 'advanced' ? 'var(--color-bg-primary)' : 'transparent',
        color: appStore.mode === 'advanced' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
        boxShadow: appStore.mode === 'advanced' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
      }"
    >
      Advanced
    </button>
  </div>
</template>
