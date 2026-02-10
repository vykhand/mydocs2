<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { Briefcase } from 'lucide-vue-next'
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold mb-6" style="color: var(--color-text-primary);">Cases</h1>
    <EmptyState
      :icon="Briefcase"
      title="Coming Soon"
      description="Case management for grouping and organizing related documents will be available in a future update."
    />
  </div>
</template>
