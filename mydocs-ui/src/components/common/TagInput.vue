<script setup lang="ts">
import { ref, computed } from 'vue'
import { X } from 'lucide-vue-next'
import { useTagsStore } from '@/stores/tags'

const props = defineProps<{
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [tags: string[]]
}>()

const tagsStore = useTagsStore()
const input = ref('')
const showSuggestions = ref(false)

const suggestions = computed(() => {
  if (!input.value) return []
  const q = input.value.toLowerCase()
  return tagsStore.allTags
    .filter(t => t.includes(q) && !props.modelValue.includes(t))
    .slice(0, 8)
})

function addTag(tag: string) {
  const cleaned = tag.toLowerCase().trim().replace(/,/g, '').slice(0, 50)
  if (cleaned && !props.modelValue.includes(cleaned)) {
    emit('update:modelValue', [...props.modelValue, cleaned])
  }
  input.value = ''
  showSuggestions.value = false
}

function removeTag(tag: string) {
  emit('update:modelValue', props.modelValue.filter(t => t !== tag))
}

function onKeydown(e: KeyboardEvent) {
  if ((e.key === 'Enter' || e.key === ',') && input.value.trim()) {
    e.preventDefault()
    addTag(input.value)
  }
  if (e.key === 'Backspace' && !input.value && props.modelValue.length > 0) {
    removeTag(props.modelValue[props.modelValue.length - 1])
  }
}

function onBlur() {
  globalThis.setTimeout(() => { showSuggestions.value = false }, 150)
}
</script>

<template>
  <div class="relative">
    <div
      class="flex flex-wrap gap-1.5 p-2 rounded-lg border min-h-[40px] cursor-text"
      style="background-color: var(--color-bg-primary); border-color: var(--color-border);"
      @click="($refs.inputEl as HTMLInputElement)?.focus()"
    >
      <span
        v-for="tag in modelValue"
        :key="tag"
        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium"
        style="background-color: var(--color-bg-tertiary); color: var(--color-text-primary);"
      >
        {{ tag }}
        <button @click.stop="removeTag(tag)" class="hover:opacity-70" aria-label="Remove tag">
          <X :size="12" />
        </button>
      </span>
      <input
        ref="inputEl"
        v-model="input"
        @keydown="onKeydown"
        @focus="showSuggestions = true"
        @blur="onBlur"
        placeholder="Add tag..."
        class="flex-1 min-w-[80px] outline-none bg-transparent text-sm"
        style="color: var(--color-text-primary);"
      />
    </div>
    <div
      v-if="showSuggestions && suggestions.length > 0"
      class="absolute z-10 w-full mt-1 rounded-lg border shadow-lg overflow-hidden"
      style="background-color: var(--color-bg-primary); border-color: var(--color-border);"
    >
      <button
        v-for="s in suggestions"
        :key="s"
        @mousedown.prevent="addTag(s)"
        class="w-full text-left px-3 py-2 text-sm hover:opacity-80 transition-opacity"
        style="color: var(--color-text-primary);"
      >
        {{ s }}
      </button>
    </div>
  </div>
</template>
