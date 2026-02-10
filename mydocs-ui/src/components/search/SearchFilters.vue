<script setup lang="ts">
import { ref } from 'vue'
import { useSearchStore } from '@/stores/search'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import TagInput from '@/components/common/TagInput.vue'

const searchStore = useSearchStore()
const expanded = ref(false)
const filterTags = ref<string[]>([])
const filterFileType = ref('')

function applyFilters() {
  if (!searchStore.config.filters) {
    searchStore.config.filters = {}
  }
  searchStore.config.filters.tags = filterTags.value.length > 0 ? filterTags.value : undefined
  searchStore.config.filters.file_type = filterFileType.value || undefined
}
</script>

<template>
  <div>
    <button
      @click="expanded = !expanded"
      class="flex items-center gap-1.5 text-sm font-medium"
      style="color: var(--color-text-secondary);"
    >
      Filters
      <ChevronDown v-if="!expanded" :size="16" />
      <ChevronUp v-else :size="16" />
    </button>
    <div v-if="expanded" class="mt-3 flex flex-wrap items-end gap-4">
      <div class="min-w-[200px]">
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Tags</label>
        <TagInput v-model="filterTags" @update:model-value="applyFilters" />
      </div>
      <div>
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">File Type</label>
        <select
          v-model="filterFileType"
          @change="applyFilters"
          class="rounded-lg border px-3 py-2 text-sm"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
        >
          <option value="">All</option>
          <option v-for="t in ['pdf', 'txt', 'docx', 'xlsx', 'pptx', 'jpeg', 'png']" :key="t" :value="t">{{ t.toUpperCase() }}</option>
        </select>
      </div>
    </div>
  </div>
</template>
