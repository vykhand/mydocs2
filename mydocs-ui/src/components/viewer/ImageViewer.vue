<script setup lang="ts">
const props = defineProps<{
  fileUrl: string
  zoom: number
}>()
</script>

<template>
  <div class="h-full overflow-auto flex justify-center items-center p-4" style="background-color: var(--color-bg-tertiary);">
    <img
      :src="fileUrl"
      class="max-w-full shadow-lg transition-transform"
      :style="{ transform: `scale(${zoom})` }"
      draggable="false"
    />
  </div>
</template>
