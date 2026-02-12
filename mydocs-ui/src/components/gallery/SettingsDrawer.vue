<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'

const emit = defineEmits<{
  close: []
}>()

const appStore = useAppStore()
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex justify-end">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative z-10 w-full max-w-md shadow-xl overflow-y-auto"
        style="background-color: var(--color-bg-primary);"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b" style="border-color: var(--color-border);">
          <h2 class="text-lg font-semibold" style="color: var(--color-text-primary);">Settings</h2>
          <button @click="emit('close')" class="p-1 rounded hover:opacity-70" style="color: var(--color-text-secondary);">
            <X :size="20" />
          </button>
        </div>

        <div class="p-6 space-y-6">
          <!-- Theme -->
          <div>
            <p class="text-sm font-medium mb-2" style="color: var(--color-text-primary);">Theme</p>
            <div class="flex gap-2">
              <button
                v-for="t in (['light', 'dark', 'system'] as const)"
                :key="t"
                @click="appStore.setTheme(t)"
                class="px-3 py-1.5 rounded-lg text-sm border capitalize"
                :style="{
                  borderColor: appStore.theme === t ? 'var(--color-accent)' : 'var(--color-border)',
                  color: appStore.theme === t ? 'var(--color-accent)' : 'var(--color-text-primary)',
                  backgroundColor: appStore.theme === t ? 'var(--color-bg-tertiary)' : 'transparent',
                }"
              >
                {{ t }}
              </button>
            </div>
          </div>

          <!-- Mode -->
          <div>
            <p class="text-sm font-medium mb-2" style="color: var(--color-text-primary);">Interface Mode</p>
            <div class="flex gap-2">
              <button
                v-for="m in (['simple', 'advanced'] as const)"
                :key="m"
                @click="appStore.mode = m"
                class="px-3 py-1.5 rounded-lg text-sm border capitalize"
                :style="{
                  borderColor: appStore.mode === m ? 'var(--color-accent)' : 'var(--color-border)',
                  color: appStore.mode === m ? 'var(--color-accent)' : 'var(--color-text-primary)',
                  backgroundColor: appStore.mode === m ? 'var(--color-bg-tertiary)' : 'transparent',
                }"
              >
                {{ m }}
              </button>
            </div>
          </div>

          <!-- About -->
          <div>
            <p class="text-sm font-medium mb-2" style="color: var(--color-text-primary);">About</p>
            <p class="text-sm" style="color: var(--color-text-secondary);">mydocs v0.1.0</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
