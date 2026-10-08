<template>
  <div v-dialog="onCancel" class="confirm-layer" @click.self="onCancel">
    <div class="confirm-card" :aria-label="title">
      <h3>{{ title }}</h3>
      <p>{{ message }}</p>
      <div class="confirm-actions">
        <button type="button" class="outline" @click="onCancel">取消</button>
        <button
          type="button"
          class="primary"
          :class="{ danger }"
          @click="onConfirm"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { dialogDirective as vDialog } from '../utils/dialog'
defineProps({
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '确定继续吗？' },
  confirmText: { type: String, default: '确定' },
  danger: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])
function onConfirm() {
  emit('confirm')
}
function onCancel() {
  emit('cancel')
}
</script>

<style scoped>
.confirm-card {
  width: min(400px, 100%);
  background: white;
  border-radius: 6px;
  padding: 26px;
  box-shadow: 0 24px 80px #15231b33;
}
.confirm-layer {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: grid;
  place-items: center;
  padding: 20px;
  background: #20302880;
  backdrop-filter: blur(3px);
  animation: modal-fade 0.18s ease;
}
.confirm-card h3 {
  margin: 0 0 12px;
  font-size: 20px;
  font-family: var(--serif);
}
.confirm-card p {
  margin: 0 0 24px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--muted);
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
