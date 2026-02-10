<script setup lang="ts">
import { useDocumentsStore } from '@/stores/documents'
import { Search, ArrowUpDown } from 'lucide-vue-next'

const docsStore = useDocumentsStore()

const statuses = ['', 'new', 'parsing', 'parsed', 'failed', 'skipped', 'not_supported']
const fileTypes = ['', 'pdf', 'txt', 'docx', 'xlsx', 'pptx', 'jpeg', 'png', 'bmp', 'tiff']
const sortOptions = [
  { value: 'created_at', label: 'Created' },
  { value: 'modified_at', label: 'Modified' },
  { value: 'original_file_name', label: 'Name' },
  { value: 'status', label: 'Status' },
]
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <div class="relative flex-1 min-w-[200px]">
      <Search
        :size="16"
        class="absolute left-3 top-1/2 -translate-y-1/2"
        style="color: var(--color-text-secondary);"
      />
      <input
        v-model="docsStore.filters.search"
        placeholder="Search by name..."
        class="w-full pl-9 pr-3 py-2 rounded-lg border text-sm"
        style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      />
    </div>

    <select
      v-model="docsStore.filters.status"
      class="rounded-lg border px-3 py-2 text-sm"
      style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
    >
      <option value="">All Statuses</option>
      <option v-for="s in statuses.slice(1)" :key="s" :value="s">{{ s }}</option>
    </select>

    <select
      v-model="docsStore.filters.file_type"
      class="rounded-lg border px-3 py-2 text-sm"
      style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
    >
      <option value="">All Types</option>
      <option v-for="t in fileTypes.slice(1)" :key="t" :value="t">{{ t.toUpperCase() }}</option>
    </select>

    <div class="flex items-center gap-1">
      <select
        v-model="docsStore.filters.sort_by"
        class="rounded-lg border px-3 py-2 text-sm"
        style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      >
        <option v-for="o in sortOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <button
        @click="docsStore.filters.sort_order = docsStore.filters.sort_order === 'desc' ? 'asc' : 'desc'"
        class="p-2 rounded-lg border"
        style="border-color: var(--color-border); color: var(--color-text-secondary);"
        :title="`Sort ${docsStore.filters.sort_order === 'desc' ? 'ascending' : 'descending'}`"
      >
        <ArrowUpDown :size="16" />
      </button>
    </div>
  </div>
</template>
