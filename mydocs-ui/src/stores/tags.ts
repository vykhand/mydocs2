import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTagsStore = defineStore('tags', () => {
  const allTags = ref<string[]>([])

  function addTags(tags: string[]) {
    const set = new Set(allTags.value)
    tags.forEach(t => set.add(t))
    allTags.value = Array.from(set).sort()
  }

  function updateFromDocuments(documents: Array<{ tags?: string[] }>) {
    const set = new Set(allTags.value)
    documents.forEach(d => {
      d.tags?.forEach(t => set.add(t))
    })
    allTags.value = Array.from(set).sort()
  }

  return { allTags, addTags, updateFromDocuments }
})
