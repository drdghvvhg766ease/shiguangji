<template>
  <span class="avatar"
    ><img
      v-if="src && !failed"
      :src="src"
      alt=""
      @error="failed = true"
    /><template v-else>{{ name.slice(0, 1) || '?' }}</template></span
  >
</template>
<script setup>
import { ref, watch } from 'vue'
const props = defineProps({
  src: { type: String, default: '' },
  name: { type: String, default: '' },
})
const failed = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
  },
)
</script>
