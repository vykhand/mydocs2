<script setup lang="ts">
import { computed } from 'vue'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const isDark = computed(() => {
  if (appStore.theme === 'dark') return true
  if (appStore.theme === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
})

const props = defineProps<{
  startDate?: string
  endDate?: string
}>()

const emit = defineEmits<{
  'update:startDate': [date: string]
  'update:endDate': [date: string]
}>()

function onStartChange(val: Date | null) {
  emit('update:startDate', val ? val.toISOString().slice(0, 10) : '')
}

function onEndChange(val: Date | null) {
  emit('update:endDate', val ? val.toISOString().slice(0, 10) : '')
}
</script>

<template>
  <div class="flex items-center gap-2">
    <VueDatePicker
      :model-value="startDate ? new Date(startDate + 'T00:00:00') : null"
      @update:model-value="onStartChange"
      :enable-time-picker="false"
      auto-apply
      placeholder="Start"
      input-class-name="dp-custom-input"
      :dark="isDark"
      class="flex-1"
    />
    <span class="text-xs shrink-0" style="color: var(--color-text-secondary);">to</span>
    <VueDatePicker
      :model-value="endDate ? new Date(endDate + 'T00:00:00') : null"
      @update:model-value="onEndChange"
      :enable-time-picker="false"
      auto-apply
      placeholder="End"
      input-class-name="dp-custom-input"
      :dark="isDark"
      class="flex-1"
    />
  </div>
</template>

<style>
.dp-custom-input {
  background-color: var(--color-bg-primary) !important;
  border-color: var(--color-border) !important;
  color: var(--color-text-primary) !important;
  border-radius: 0.25rem;
  padding: 0.375rem 0.5rem;
  font-size: 0.875rem;
}
</style>
