<script setup lang="ts">
import { Check, AlertCircle } from 'lucide-vue-next'

defineProps<{
  progress: number
  uploading: boolean
  result: { documents: any[]; skipped: any[] } | null
}>()
</script>

<template>
  <div
    class="rounded-lg border p-4 space-y-3"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
  >
    <div v-if="uploading">
      <div class="flex justify-between text-sm mb-1">
        <span style="color: var(--color-text-primary);">Uploading...</span>
        <span style="color: var(--color-text-secondary);">{{ progress }}%</span>
      </div>
      <div class="w-full h-2 rounded-full overflow-hidden" style="background-color: var(--color-bg-tertiary);">
        <div
          class="h-full rounded-full transition-all duration-300"
          style="background-color: var(--color-accent);"
          :style="{ width: progress + '%' }"
        />
      </div>
    </div>

    <div v-if="result" class="space-y-2">
      <div v-if="result.documents.length > 0" class="flex items-start gap-2">
        <Check :size="18" style="color: var(--color-success);" class="mt-0.5 shrink-0" />
        <div>
          <p class="text-sm font-medium" style="color: var(--color-text-primary);">
            {{ result.documents.length }} document(s) ingested
          </p>
          <p
            v-for="doc in result.documents"
            :key="doc.id"
            class="text-xs mt-0.5"
            style="color: var(--color-text-secondary);"
          >
            {{ doc.file_name }} ({{ doc.status }})
          </p>
        </div>
      </div>
      <div v-if="result.skipped.length > 0" class="flex items-start gap-2">
        <AlertCircle :size="18" style="color: var(--color-warning);" class="mt-0.5 shrink-0" />
        <div>
          <p class="text-sm font-medium" style="color: var(--color-text-primary);">
            {{ result.skipped.length }} file(s) skipped
          </p>
          <p
            v-for="(s, i) in result.skipped"
            :key="i"
            class="text-xs mt-0.5"
            style="color: var(--color-text-secondary);"
          >
            {{ s.path }}: {{ s.reason }}
          </p>
        </div>
      </div>
      <router-link
        to="/documents"
        class="inline-block mt-2 text-sm font-medium"
        style="color: var(--color-accent);"
      >
        View Documents
      </router-link>
    </div>
  </div>
</template>
