<script setup lang="ts">
import { ref } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useRoute, useRouter } from 'vue-router'
import { X } from 'lucide-vue-next'
import TagInput from '@/components/common/TagInput.vue'

const emit = defineEmits<{
  close: []
}>()

const route = useRoute()
const router = useRouter()
const docsStore = useDocumentsStore()

const statusOptions = [
  { value: 'new', label: 'New' },
  { value: 'parsing', label: 'Parsing' },
  { value: 'parsed', label: 'Parsed' },
  { value: 'failed', label: 'Failed' },
]

const fileTypeOptions = [
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'DOCX' },
  { value: 'xlsx', label: 'XLSX' },
  { value: 'pptx', label: 'PPTX' },
  { value: 'jpeg', label: 'JPEG' },
  { value: 'png', label: 'PNG' },
  { value: 'txt', label: 'TXT' },
]

function applyFilters() {
  const query: Record<string, string> = {}
  if (route.query.q) query.q = route.query.q as string
  if (docsStore.filters.status) query.status = docsStore.filters.status
  if (docsStore.filters.file_type) query.file_type = docsStore.filters.file_type
  if (docsStore.filters.tags) query.tags = docsStore.filters.tags
  router.replace({ path: route.path, query })
  emit('close')
}

function clearFilters() {
  docsStore.filters.status = undefined
  docsStore.filters.file_type = undefined
  docsStore.filters.tags = undefined
  docsStore.filters.document_type = undefined
  docsStore.filters.date_from = undefined
  docsStore.filters.date_to = undefined
  applyFilters()
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-end">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative z-10 w-full max-h-[80vh] rounded-t-xl overflow-y-auto"
        style="background-color: var(--color-bg-primary);"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b sticky top-0" style="border-color: var(--color-border); background-color: var(--color-bg-primary);">
          <h3 class="text-base font-semibold" style="color: var(--color-text-primary);">Filters</h3>
          <button @click="emit('close')" class="p-1 rounded" style="color: var(--color-text-secondary);">
            <X :size="20" />
          </button>
        </div>

        <div class="p-4 space-y-4">
          <!-- Status -->
          <div>
            <p class="text-sm font-medium mb-2" style="color: var(--color-text-primary);">Status</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="opt in statusOptions"
                :key="opt.value"
                @click="docsStore.filters.status = docsStore.filters.status === opt.value ? undefined : opt.value"
                class="px-3 py-1.5 rounded-full text-sm border"
                :style="{
                  borderColor: docsStore.filters.status === opt.value ? 'var(--color-accent)' : 'var(--color-border)',
                  color: docsStore.filters.status === opt.value ? 'var(--color-accent)' : 'var(--color-text-primary)',
                  backgroundColor: docsStore.filters.status === opt.value ? 'var(--color-bg-tertiary)' : 'transparent',
                }"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <!-- File Type -->
          <div>
            <p class="text-sm font-medium mb-2" style="color: var(--color-text-primary);">File Type</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="opt in fileTypeOptions"
                :key="opt.value"
                @click="docsStore.filters.file_type = docsStore.filters.file_type === opt.value ? undefined : opt.value"
                class="px-3 py-1.5 rounded-full text-sm border"
                :style="{
                  borderColor: docsStore.filters.file_type === opt.value ? 'var(--color-accent)' : 'var(--color-border)',
                  color: docsStore.filters.file_type === opt.value ? 'var(--color-accent)' : 'var(--color-text-primary)',
                  backgroundColor: docsStore.filters.file_type === opt.value ? 'var(--color-bg-tertiary)' : 'transparent',
                }"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <!-- Sort -->
          <div>
            <p class="text-sm font-medium mb-2" style="color: var(--color-text-primary);">Sort By</p>
            <select
              class="w-full px-3 py-2 rounded-lg border text-sm"
              style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
              v-model="docsStore.filters.sort_by"
            >
              <option value="created_at">Created Date</option>
              <option value="modified_at">Modified Date</option>
              <option value="original_file_name">Name</option>
            </select>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex gap-3 px-4 py-3 border-t sticky bottom-0" style="border-color: var(--color-border); background-color: var(--color-bg-primary);">
          <button
            @click="clearFilters"
            class="flex-1 px-4 py-2.5 rounded-lg text-sm border"
            style="border-color: var(--color-border); color: var(--color-text-primary);"
          >
            Clear
          </button>
          <button
            @click="applyFilters"
            class="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-white"
            style="background-color: var(--color-accent);"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
