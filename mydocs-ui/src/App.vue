<script setup lang="ts">
import AppShell from '@/components/layout/AppShell.vue'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'

useKeyboardShortcuts()
</script>

<template>
  <AppShell>
    <RouterView />
  </AppShell>
</template>
