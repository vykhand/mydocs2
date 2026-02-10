<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'default'
}>(), {
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  variant: 'default',
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('cancel')
  if (e.key === 'Enter') emit('confirm')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="emit('cancel')" />
      <div
        class="relative z-10 w-full max-w-md mx-4 p-6 rounded-xl shadow-xl"
        style="background-color: var(--color-bg-primary);"
      >
        <h3 class="text-lg font-semibold mb-2" style="color: var(--color-text-primary);">{{ title }}</h3>
        <p class="text-sm mb-6" style="color: var(--color-text-secondary);">{{ message }}</p>
        <div class="flex justify-end gap-3">
          <button
            @click="emit('cancel')"
            class="px-4 py-2 rounded-lg text-sm font-medium border transition-colors"
            style="border-color: var(--color-border); color: var(--color-text-primary);"
          >
            {{ cancelLabel }}
          </button>
          <button
            @click="emit('confirm')"
            class="px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors"
            :style="{
              backgroundColor: variant === 'danger' ? 'var(--color-danger)' : 'var(--color-accent)',
            }"
          >
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
