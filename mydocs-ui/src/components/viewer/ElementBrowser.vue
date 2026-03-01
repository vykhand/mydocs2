<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import type { DocumentElement } from '@/types'
import { ELEMENT_TYPE_BORDER_COLORS, ELEMENT_TYPE_LABELS } from '@/types'
import ElementCard from './ElementCard.vue'

const props = defineProps<{
  elements: DocumentElement[]
  currentPage: number
  activeElementId: string | null
}>()

const emit = defineEmits<{
  select: [elementId: string]
  'go-to-page': [pageNumber: number]
}>()

const showAllPages = ref(false)
const collapsedGroups = ref<Set<string>>(new Set())

const displayedElements = computed(() => {
  if (showAllPages.value) return props.elements
  return props.elements.filter(el => el.page_number === props.currentPage)
})

const elementsByType = computed<Record<string, DocumentElement[]>>(() => {
  const grouped: Record<string, DocumentElement[]> = {}
  for (const el of displayedElements.value) {
    if (!grouped[el.type]) grouped[el.type] = []
    grouped[el.type].push(el)
  }
  return grouped
})

function toggleGroup(type: string) {
  const next = new Set(collapsedGroups.value)
  if (next.has(type)) {
    next.delete(type)
  } else {
    next.add(type)
  }
  collapsedGroups.value = next
}

function handleSelect(elementId: string) {
  const el = props.elements.find(e => e.id === elementId)
  if (el && el.page_number !== props.currentPage) {
    emit('go-to-page', el.page_number)
  }
  emit('select', elementId)
}
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden" style="background-color: var(--color-bg-secondary);">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 py-2 border-b shrink-0" style="border-color: var(--color-border);">
      <div class="flex items-center gap-2">
        <label class="flex items-center gap-1.5 text-xs cursor-pointer" style="color: var(--color-text-secondary);">
          <input
            type="checkbox"
            :checked="showAllPages"
            @change="showAllPages = !showAllPages"
            class="rounded border"
          />
          All pages
        </label>
      </div>
      <span class="text-xs tabular-nums" style="color: var(--color-text-secondary);">
        {{ displayedElements.length }} element{{ displayedElements.length !== 1 ? 's' : '' }}
      </span>
    </div>

    <!-- Element groups -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="displayedElements.length === 0" class="flex items-center justify-center h-full">
        <p class="text-xs" style="color: var(--color-text-secondary);">No elements on this page</p>
      </div>

      <div v-for="(typeElements, type) in elementsByType" :key="type" class="border-b" style="border-color: var(--color-border);">
        <!-- Group header -->
        <button
          class="flex items-center gap-2 w-full px-3 py-2 text-xs font-medium hover:opacity-80 transition-opacity"
          style="color: var(--color-text-primary);"
          @click="toggleGroup(type as string)"
        >
          <ChevronDown
            :size="14"
            class="transition-transform duration-150 shrink-0"
            :class="{ '-rotate-90': collapsedGroups.has(type as string) }"
            style="color: var(--color-text-secondary);"
          />
          <span
            class="inline-block w-2.5 h-2.5 rounded-full shrink-0"
            :style="{ backgroundColor: ELEMENT_TYPE_BORDER_COLORS[type as keyof typeof ELEMENT_TYPE_BORDER_COLORS] }"
          />
          {{ ELEMENT_TYPE_LABELS[type as keyof typeof ELEMENT_TYPE_LABELS] || type }}
          <span class="text-[10px] tabular-nums" style="color: var(--color-text-secondary);">
            ({{ typeElements.length }})
          </span>
        </button>

        <!-- Group content -->
        <div v-if="!collapsedGroups.has(type as string)" class="px-2 pb-2 space-y-1">
          <ElementCard
            v-for="el in typeElements"
            :key="el.id"
            :element="el"
            :is-active="activeElementId === el.id"
            @select="handleSelect"
          />
        </div>
      </div>
    </div>
  </div>
</template>
