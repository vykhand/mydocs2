<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useDocumentsStore } from '@/stores/documents'
import { useSearchStore } from '@/stores/search'
import { Filter, ChevronDown, Search } from 'lucide-vue-next'
import TagInput from '@/components/common/TagInput.vue'
import DateRangePicker from '@/components/common/DateRangePicker.vue'
import { ref, computed } from 'vue'

defineProps<{
  collapsed: boolean
}>()

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const docsStore = useDocumentsStore()
const searchStore = useSearchStore()

const showStatusFilter = ref(false)
const showFileTypeFilter = ref(false)
const showSorting = ref(false)
const showAdvancedSearch = ref(false)

// Status options
const statusOptions = [
  { value: 'new', label: 'New' },
  { value: 'parsing', label: 'Parsing' },
  { value: 'parsed', label: 'Parsed' },
  { value: 'failed', label: 'Failed' },
]

// File type options
const fileTypeOptions = [
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'DOCX' },
  { value: 'xlsx', label: 'XLSX' },
  { value: 'pptx', label: 'PPTX' },
  { value: 'jpeg', label: 'JPEG' },
  { value: 'png', label: 'PNG' },
  { value: 'txt', label: 'TXT' },
]

function toggleStatusFilter(val: string) {
  docsStore.filters.status = docsStore.filters.status === val ? undefined : val
  syncFiltersToUrl()
}

function toggleFileTypeFilter(val: string) {
  docsStore.filters.file_type = docsStore.filters.file_type === val ? undefined : val
  syncFiltersToUrl()
}

function syncFiltersToUrl() {
  const query: Record<string, string> = {}
  if (route.query.q) query.q = route.query.q as string
  if (docsStore.filters.status) query.status = docsStore.filters.status
  if (docsStore.filters.file_type) query.file_type = docsStore.filters.file_type
  if (docsStore.filters.tags) query.tags = docsStore.filters.tags
  if (docsStore.filters.sort_by && docsStore.filters.sort_by !== 'created_at') query.sort_by = docsStore.filters.sort_by
  if (docsStore.filters.sort_order && docsStore.filters.sort_order !== 'desc') query.sort_order = docsStore.filters.sort_order
  router.replace({ path: route.path, query })
}

// Active filter chips
const activeFilterChips = computed(() => {
  const chips: Array<{ key: string; label: string }> = []
  if (docsStore.filters.status) chips.push({ key: 'status', label: `Status: ${docsStore.filters.status}` })
  if (docsStore.filters.file_type) chips.push({ key: 'file_type', label: `Type: ${docsStore.filters.file_type}` })
  if (docsStore.filters.tags) chips.push({ key: 'tags', label: `Tags: ${docsStore.filters.tags}` })
  return chips
})

function removeChip(key: string) {
  if (key === 'status') docsStore.filters.status = undefined
  if (key === 'file_type') docsStore.filters.file_type = undefined
  if (key === 'tags') docsStore.filters.tags = undefined
  syncFiltersToUrl()
}

// Search mode options
const searchModes = [
  { value: 'fulltext' as const, label: 'Fulltext' },
  { value: 'vector' as const, label: 'Vector' },
  { value: 'hybrid' as const, label: 'Hybrid' },
]
</script>

<template>
  <nav
    class="shrink-0 border-r flex flex-col transition-all duration-200 overflow-hidden overflow-y-auto"
    :style="{
      width: collapsed ? 'var(--width-sidebar-collapsed)' : 'var(--width-sidebar-expanded)',
      backgroundColor: 'var(--color-bg-secondary)',
      borderColor: 'var(--color-border)',
    }"
  >
    <!-- Collapsed: just show filter icon -->
    <div v-if="collapsed" class="flex flex-col items-center gap-2 py-3">
      <button
        class="p-2 rounded-md hover:opacity-80"
        style="color: var(--color-text-secondary);"
        title="Filters"
      >
        <Filter :size="18" />
      </button>
      <button
        class="p-2 rounded-md hover:opacity-80"
        style="color: var(--color-text-secondary);"
        title="Search Settings"
      >
        <Search :size="18" />
      </button>
    </div>

    <!-- Expanded sidebar content -->
    <div v-else class="flex-1 p-3 space-y-4">
      <!-- Active filter chips -->
      <div v-if="activeFilterChips.length" class="flex flex-wrap gap-1.5">
        <span
          v-for="chip in activeFilterChips"
          :key="chip.key"
          class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs cursor-pointer"
          style="background-color: var(--color-accent); color: white;"
          @click="removeChip(chip.key)"
        >
          {{ chip.label }}
          <span class="text-white/80">&times;</span>
        </span>
      </div>

      <!-- Status filter -->
      <div>
        <button
          @click="showStatusFilter = !showStatusFilter"
          class="flex items-center gap-1 text-xs font-medium mb-2 uppercase tracking-wide w-full"
          style="color: var(--color-text-secondary);"
        >
          <ChevronDown :size="14" :class="{ 'rotate-180': showStatusFilter }" class="transition-transform" />
          Status
        </button>
        <div v-if="showStatusFilter" class="space-y-1">
          <label
            v-for="opt in statusOptions"
            :key="opt.value"
            class="flex items-center gap-2 px-2 py-1 rounded text-sm cursor-pointer hover:opacity-80"
            :style="{ color: docsStore.filters.status === opt.value ? 'var(--color-accent)' : 'var(--color-text-primary)' }"
          >
            <input
              type="checkbox"
              :checked="docsStore.filters.status === opt.value"
              @change="toggleStatusFilter(opt.value)"
              class="rounded"
            />
            {{ opt.label }}
          </label>
        </div>
      </div>

      <!-- File Type filter -->
      <div>
        <button
          @click="showFileTypeFilter = !showFileTypeFilter"
          class="flex items-center gap-1 text-xs font-medium mb-2 uppercase tracking-wide w-full"
          style="color: var(--color-text-secondary);"
        >
          <ChevronDown :size="14" :class="{ 'rotate-180': showFileTypeFilter }" class="transition-transform" />
          File Type
        </button>
        <div v-if="showFileTypeFilter" class="space-y-1">
          <label
            v-for="opt in fileTypeOptions"
            :key="opt.value"
            class="flex items-center gap-2 px-2 py-1 rounded text-sm cursor-pointer hover:opacity-80"
            :style="{ color: docsStore.filters.file_type === opt.value ? 'var(--color-accent)' : 'var(--color-text-primary)' }"
          >
            <input
              type="checkbox"
              :checked="docsStore.filters.file_type === opt.value"
              @change="toggleFileTypeFilter(opt.value)"
              class="rounded"
            />
            {{ opt.label }}
          </label>
        </div>
      </div>

      <!-- Document Type filter -->
      <div>
        <p class="text-xs font-medium mb-2 uppercase tracking-wide" style="color: var(--color-text-secondary);">Document Type</p>
        <select
          class="w-full px-2 py-1.5 rounded border text-sm"
          style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
          :value="docsStore.filters.document_type || ''"
          @change="docsStore.filters.document_type = ($event.target as HTMLSelectElement).value || undefined; syncFiltersToUrl()"
        >
          <option value="">All</option>
          <option value="generic">Generic</option>
        </select>
      </div>

      <!-- Tags -->
      <div>
        <p class="text-xs font-medium mb-2 uppercase tracking-wide" style="color: var(--color-text-secondary);">Tags</p>
        <TagInput :model-value="docsStore.filters.tags ? docsStore.filters.tags.split(',') : []" @update:model-value="(v: string[]) => { docsStore.filters.tags = v.length ? v.join(',') : undefined; syncFiltersToUrl() }" />
      </div>

      <!-- Date Range -->
      <div>
        <p class="text-xs font-medium mb-2 uppercase tracking-wide" style="color: var(--color-text-secondary);">Date Range</p>
        <DateRangePicker />
      </div>

      <!-- Sorting -->
      <div>
        <button
          @click="showSorting = !showSorting"
          class="flex items-center gap-1 text-xs font-medium mb-2 uppercase tracking-wide w-full"
          style="color: var(--color-text-secondary);"
        >
          <ChevronDown :size="14" :class="{ 'rotate-180': showSorting }" class="transition-transform" />
          Sorting
        </button>
        <div v-if="showSorting" class="space-y-2">
          <select
            class="w-full px-2 py-1.5 rounded border text-sm"
            style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
            v-model="docsStore.filters.sort_by"
            @change="syncFiltersToUrl()"
          >
            <option value="created_at">Created Date</option>
            <option value="modified_at">Modified Date</option>
            <option value="file_metadata.size_bytes">Size</option>
            <option value="file_metadata.page_count">Page Count</option>
            <option value="original_file_name">Name</option>
          </select>
          <select
            class="w-full px-2 py-1.5 rounded border text-sm"
            style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
            v-model="docsStore.filters.sort_order"
            @change="syncFiltersToUrl()"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
      </div>

      <!-- Advanced Search Settings -->
      <div>
        <button
          @click="showAdvancedSearch = !showAdvancedSearch"
          class="flex items-center gap-1 text-xs font-medium uppercase tracking-wide w-full"
          style="color: var(--color-text-secondary);"
        >
          <ChevronDown :size="14" :class="{ 'rotate-180': showAdvancedSearch }" class="transition-transform" />
          Advanced Search
        </button>
        <div v-if="showAdvancedSearch" class="mt-2 space-y-3">
          <!-- Search mode -->
          <div>
            <p class="text-xs mb-1" style="color: var(--color-text-secondary);">Search Mode</p>
            <div class="flex gap-1">
              <button
                v-for="sm in searchModes"
                :key="sm.value"
                @click="searchStore.searchMode = sm.value"
                class="flex-1 px-2 py-1 text-xs rounded border"
                :style="{
                  borderColor: searchStore.searchMode === sm.value ? 'var(--color-accent)' : 'var(--color-border)',
                  color: searchStore.searchMode === sm.value ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                  backgroundColor: searchStore.searchMode === sm.value ? 'var(--color-bg-tertiary)' : 'transparent',
                }"
              >
                {{ sm.label }}
              </button>
            </div>
          </div>

          <!-- Fulltext config -->
          <div v-if="searchStore.searchMode === 'fulltext' || searchStore.searchMode === 'hybrid'">
            <p class="text-xs mb-1 font-medium" style="color: var(--color-text-secondary);">Fulltext</p>
            <div class="space-y-1.5">
              <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                <input type="checkbox" v-model="searchStore.config.fulltext!.fuzzy.enabled" class="rounded" />
                Fuzzy matching
              </label>
              <div v-if="searchStore.config.fulltext?.fuzzy.enabled" class="pl-4 space-y-1">
                <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                  Max edits
                  <input type="number" v-model.number="searchStore.config.fulltext!.fuzzy.max_edits" min="1" max="2" class="w-14 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
                </label>
                <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                  Prefix length
                  <input type="number" v-model.number="searchStore.config.fulltext!.fuzzy.prefix_length" min="0" max="10" class="w-14 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
                </label>
              </div>
              <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                Score boost
                <input type="number" v-model.number="searchStore.config.fulltext!.score_boost" min="0" step="0.1" class="w-14 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
              </label>
            </div>
          </div>

          <!-- Vector config -->
          <div v-if="searchStore.searchMode === 'vector' || searchStore.searchMode === 'hybrid'">
            <p class="text-xs mb-1 font-medium" style="color: var(--color-text-secondary);">Vector</p>
            <div class="space-y-1.5">
              <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                Num candidates
                <input type="number" v-model.number="searchStore.config.vector!.num_candidates" min="10" max="500" class="w-16 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
              </label>
              <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                Score boost
                <input type="number" v-model.number="searchStore.config.vector!.score_boost" min="0" step="0.1" class="w-14 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
              </label>
            </div>
          </div>

          <!-- Hybrid config -->
          <div v-if="searchStore.searchMode === 'hybrid'">
            <p class="text-xs mb-1 font-medium" style="color: var(--color-text-secondary);">Hybrid</p>
            <div class="space-y-1.5">
              <div class="flex gap-1">
                <button
                  @click="searchStore.config.hybrid!.combination_method = 'rrf'"
                  class="flex-1 px-2 py-1 text-xs rounded border"
                  :style="{
                    borderColor: searchStore.config.hybrid?.combination_method === 'rrf' ? 'var(--color-accent)' : 'var(--color-border)',
                    color: searchStore.config.hybrid?.combination_method === 'rrf' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                  }"
                >RRF</button>
                <button
                  @click="searchStore.config.hybrid!.combination_method = 'weighted_sum'"
                  class="flex-1 px-2 py-1 text-xs rounded border"
                  :style="{
                    borderColor: searchStore.config.hybrid?.combination_method === 'weighted_sum' ? 'var(--color-accent)' : 'var(--color-border)',
                    color: searchStore.config.hybrid?.combination_method === 'weighted_sum' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                  }"
                >Weighted</button>
              </div>
              <label v-if="searchStore.config.hybrid?.combination_method === 'rrf'" class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                RRF K
                <input type="number" v-model.number="searchStore.config.hybrid!.rrf_k" min="1" max="1000" class="w-16 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
              </label>
            </div>
          </div>

          <!-- Global search params -->
          <div>
            <p class="text-xs mb-1 font-medium" style="color: var(--color-text-secondary);">Global</p>
            <div class="space-y-1.5">
              <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                Top K
                <input type="number" v-model.number="searchStore.config.top_k" min="1" max="100" class="w-14 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
              </label>
              <label class="flex items-center gap-2 text-xs" style="color: var(--color-text-secondary);">
                Min score
                <input type="number" v-model.number="searchStore.config.min_score" min="0" max="1" step="0.05" class="w-16 px-1 py-0.5 rounded border text-xs" style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>
