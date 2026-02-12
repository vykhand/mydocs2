<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useDocumentsStore } from '@/stores/documents'
import { FileText, Briefcase, Filter, ChevronDown } from 'lucide-vue-next'
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

const showAdvancedFilters = ref(false)
const showStatusFilter = ref(true)
const showFileTypeFilter = ref(true)

const tabs = [
  { key: 'documents' as const, label: 'Documents', icon: FileText },
  { key: 'cases' as const, label: 'Cases', icon: Briefcase },
]

function setActiveTab(tab: 'documents' | 'cases') {
  appStore.activeTab = tab
  if (tab === 'documents') {
    router.push({ path: '/', query: route.query })
  } else {
    router.push('/cases')
  }
}

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
    <!-- Tab buttons -->
    <div class="flex border-b shrink-0" style="border-color: var(--color-border);">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="setActiveTab(tab.key)"
        class="flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors border-b-2"
        :style="{
          color: appStore.activeTab === tab.key ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          borderBottomColor: appStore.activeTab === tab.key ? 'var(--color-accent)' : 'transparent',
        }"
        :title="collapsed ? tab.label : undefined"
      >
        <component :is="tab.icon" :size="18" class="shrink-0" />
        <span v-if="!collapsed">{{ tab.label }}</span>
      </button>
    </div>

    <!-- Collapsed: just show filter icon -->
    <div v-if="collapsed" class="flex flex-col items-center gap-2 py-3">
      <button
        class="p-2 rounded-md hover:opacity-80"
        style="color: var(--color-text-secondary);"
        title="Filters"
      >
        <Filter :size="18" />
      </button>
    </div>

    <!-- Documents tab content -->
    <div v-else-if="appStore.activeTab === 'documents'" class="flex-1 p-3 space-y-4">
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

      <!-- Sort controls -->
      <div>
        <p class="text-xs font-medium mb-2 uppercase tracking-wide" style="color: var(--color-text-secondary);">Sort By</p>
        <select
          class="w-full px-2 py-1.5 rounded border text-sm mb-2"
          style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
          v-model="docsStore.filters.sort_by"
          @change="syncFiltersToUrl()"
        >
          <option value="created_at">Created Date</option>
          <option value="modified_at">Modified Date</option>
          <option value="original_file_name">Name</option>
          <option value="status">Status</option>
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

      <!-- Advanced Filters (collapsed by default) -->
      <div>
        <button
          @click="showAdvancedFilters = !showAdvancedFilters"
          class="flex items-center gap-1 text-xs font-medium uppercase tracking-wide"
          style="color: var(--color-text-secondary);"
        >
          <ChevronDown :size="14" :class="{ 'rotate-180': showAdvancedFilters }" class="transition-transform" />
          Advanced Filters
        </button>
        <div v-if="showAdvancedFilters" class="mt-2 space-y-3">
          <div>
            <p class="text-xs mb-1" style="color: var(--color-text-secondary);">Tags</p>
            <TagInput :model-value="docsStore.filters.tags ? docsStore.filters.tags.split(',') : []" @update:model-value="(v: string[]) => { docsStore.filters.tags = v.length ? v.join(',') : undefined; syncFiltersToUrl() }" />
          </div>
          <div>
            <p class="text-xs mb-1" style="color: var(--color-text-secondary);">Date Range</p>
            <DateRangePicker />
          </div>
        </div>
      </div>
    </div>

    <!-- Cases tab content -->
    <div v-else-if="appStore.activeTab === 'cases' && !collapsed" class="flex-1 p-3 space-y-3">
      <button
        @click="router.push('/cases')"
        class="w-full px-3 py-2 rounded-lg text-sm font-medium text-white"
        style="background-color: var(--color-accent);"
      >
        + New Case
      </button>
      <p class="text-xs" style="color: var(--color-text-secondary);">
        Cases will appear here once created.
      </p>
    </div>
  </nav>
</template>
