<script setup lang="ts">
import { type Component } from 'vue'
import { Inbox } from 'lucide-vue-next'

withDefaults(defineProps<{
  icon?: Component
  title: string
  description?: string
  actionLabel?: string
}>(), {
  icon: () => Inbox,
})

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 px-4 text-center">
    <component
      :is="icon"
      :size="48"
      class="mb-4"
      style="color: var(--color-text-secondary); opacity: 0.5;"
    />
    <h3 class="text-lg font-semibold mb-1" style="color: var(--color-text-primary);">{{ title }}</h3>
    <p v-if="description" class="text-sm max-w-sm mb-4" style="color: var(--color-text-secondary);">{{ description }}</p>
    <button
      v-if="actionLabel"
      @click="emit('action')"
      class="px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors"
      style="background-color: var(--color-accent);"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>
