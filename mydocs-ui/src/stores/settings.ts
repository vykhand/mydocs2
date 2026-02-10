import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SearchMode } from '@/types'

export const useSettingsStore = defineStore('settings', () => {
  const defaultSearchMode = ref<SearchMode>('hybrid')
  const defaultTopK = ref(10)
  const defaultParserModel = ref('prebuilt-layout')
  const defaultEmbeddingModel = ref('azure/text-embedding-3-large')

  return { defaultSearchMode, defaultTopK, defaultParserModel, defaultEmbeddingModel }
}, {
  persist: true,
})
