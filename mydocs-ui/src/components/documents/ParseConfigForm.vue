<script setup lang="ts">
import { ref } from 'vue'

const model = ref('prebuilt-layout')
const embeddingModel = ref('azure/text-embedding-3-large')
const embeddingDimensions = ref(3072)

const emit = defineEmits<{
  submit: [config: Record<string, any>]
}>()

function submit() {
  emit('submit', {
    azure_di_model: model.value,
    page_embeddings: [{
      model: embeddingModel.value,
      dimensions: embeddingDimensions.value,
    }],
  })
}
</script>

<template>
  <div class="space-y-3">
    <div>
      <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Azure DI Model</label>
      <input
        v-model="model"
        class="w-full rounded-lg border px-3 py-2 text-sm"
        style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      />
    </div>
    <div>
      <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Embedding Model</label>
      <input
        v-model="embeddingModel"
        class="w-full rounded-lg border px-3 py-2 text-sm"
        style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      />
    </div>
    <div>
      <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Dimensions</label>
      <input
        v-model.number="embeddingDimensions"
        type="number"
        class="w-full rounded-lg border px-3 py-2 text-sm"
        style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      />
    </div>
    <button
      @click="submit"
      class="px-4 py-2 rounded-lg text-sm font-medium text-white"
      style="background-color: var(--color-accent);"
    >
      Parse with Config
    </button>
  </div>
</template>
