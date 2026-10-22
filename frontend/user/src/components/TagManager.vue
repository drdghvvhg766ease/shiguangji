<template>
  <div v-dialog="close" class="tag-layer" @click.self="close">
    <div
      ref="card"
      class="tag-card"
      data-dialog-panel
      role="dialog"
      aria-label="管理活动标签"
    >
      <header class="tag-head">
        <div>
          <span class="eyebrow">TAGS / 记录分类</span>
          <h3>管理活动标签</h3>
        </div>
        <button class="icon-button" type="button" title="关闭" @click="close">
          <X :size="18" />
        </button>
      </header>

      <p class="tag-hint">
        改名会同步到圈内所有记录；删除后这些记录会归到「{{ fallbackName }}」。
      </p>

      <ul class="tag-rows">
        <li
          v-for="row in rows"
          :key="row.key"
          class="tag-row"
          :class="{ removed: row.removed, fresh: row.isNew }"
        >
          <span class="tag-dot" aria-hidden="true"></span>
          <input
            v-model="row.name"
            type="text"
            maxlength="20"
            :aria-label="`标签名称：${row.original || row.name}`"
            :disabled="row.removed"
          />
          <span class="tag-count">
            {{ row.isNew ? '新标签' : `${row.post_count} 条` }}
          </span>
          <button
            class="icon-button tag-remove"
            type="button"
            :title="row.removed ? '撤销删除' : '删除标签'"
            :aria-label="row.removed ? '撤销删除' : '删除标签'"
            @click="toggleRemove(row)"
          >
            <Undo2 v-if="row.removed" :size="15" />
            <Trash2 v-else :size="15" />
          </button>
        </li>
      </ul>

      <form class="tag-add" @submit.prevent="addRow">
        <input
          v-model="draft"
          type="text"
          maxlength="20"
          placeholder="新增标签，比如：露营"
          aria-label="新增标签名称"
        />
        <button class="outline" type="submit" :disabled="!canAdd">
          <Plus :size="15" />添加
        </button>
      </form>

      <footer class="tag-foot">
        <p class="tag-error" role="alert">{{ error }}</p>
        <div class="tag-actions">
          <button class="outline" type="button" :disabled="saving" @click="close">
            取消
          </button>
          <button class="primary" type="button" :disabled="saving || !dirty" @click="save">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Plus, Trash2, Undo2, X } from 'lucide-vue-next'
import api from '../api'
import { dialogDirective as vDialog } from '../utils/dialog'

const card = ref(null)
const props = defineProps({
  circleId: { type: Number, required: true },
  tags: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])

const rows = ref([])
const draft = ref('')
const error = ref('')
const saving = ref(false)
let seq = 0

function hydrate() {
  rows.value = props.tags.map((tag) => ({
    key: `t${tag.id}`,
    id: tag.id,
    name: tag.name,
    original: tag.name,
    post_count: tag.post_count || 0,
    removed: false,
    isNew: false,
  }))
}

const active = computed(() => rows.value.filter((row) => !row.removed))
const fallbackName = computed(() => {
  const names = active.value.map((row) => row.name.trim()).filter(Boolean)
  return names.includes('日常') ? '日常' : names[0] || '日常'
})
const canAdd = computed(() => {
  const value = draft.value.trim()
  return !!value && !rows.value.some((row) => !row.removed && row.name.trim() === value)
})
const dirty = computed(() =>
  rows.value.some(
    (row) => row.isNew || row.removed || row.name.trim() !== row.original.trim(),
  ),
)

function toggleRemove(row) {
  if (row.isNew) {
    rows.value = rows.value.filter((item) => item !== row)
    return
  }
  row.removed = !row.removed
  error.value = ''
}

function addRow() {
  const value = draft.value.trim()
  if (!value) return
  if (rows.value.some((row) => !row.removed && row.name.trim() === value)) {
    error.value = '这个标签已经存在'
    return
  }
  rows.value.push({
    key: `new${++seq}`,
    id: 0,
    name: value,
    original: '',
    post_count: 0,
    removed: false,
    isNew: true,
  })
  draft.value = ''
  error.value = ''
}

async function save() {
  error.value = ''
  const activeRows = rows.value.filter((row) => !row.removed)
  if (!activeRows.length) {
    error.value = '至少保留一个标签'
    return
  }
  const names = activeRows.map((row) => row.name.trim())
  if (names.some((name) => !name)) {
    error.value = '标签名称不能为空'
    return
  }
  if (new Set(names).size !== names.length) {
    error.value = '标签名称不能重复'
    return
  }
  saving.value = true
  const base = `/api/circles/${props.circleId}/tags`
  try {
    for (const row of activeRows) {
      if (!row.isNew && row.name.trim() !== row.original.trim()) {
        await api.patch(`${base}/${row.id}`, { name: row.name.trim() })
      }
    }
    for (const row of activeRows) {
      if (row.isNew) await api.post(base, { name: row.name.trim() })
    }
    const fallback = fallbackName.value
    for (const row of rows.value) {
      if (!row.isNew && row.removed) {
        await api.delete(`${base}/${row.id}`, { params: { fallback } })
      }
    }
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = e.userMessage || '保存失败，请稍后再试'
    await refresh()
  } finally {
    saving.value = false
  }
}

async function refresh() {
  try {
    const { data } = await api.get(`/api/circles/${props.circleId}/tags`)
    rows.value = data.map((tag) => ({
      key: `t${tag.id}`,
      id: tag.id,
      name: tag.name,
      original: tag.name,
      post_count: tag.post_count || 0,
      removed: false,
      isNew: false,
    }))
  } catch {
    /* 刷新失败时保留当前编辑内容 */
  }
}

function close() {
  emit('close')
}

onMounted(async () => {
  hydrate()
  await nextTick()
  card.value?.focus({ preventScroll: true })
})
</script>

<style scoped>
.tag-layer {
  position: fixed;
  inset: 0;
  z-index: 210;
  display: grid;
  place-items: center;
  padding: 20px;
  background: #1a2426a6;
  backdrop-filter: blur(4px);
  animation: modal-fade 0.18s ease;
}
.tag-card {
  width: min(480px, 100%);
  max-height: min(86vh, 720px);
  display: flex;
  flex-direction: column;
  padding: 20px 20px 16px;
  border-radius: 22px;
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-lg);
  color: var(--ink);
}
.tag-card:focus,
.tag-card:focus-visible {
  outline: none;
}
.tag-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.tag-head h3 {
  margin: 4px 0 0;
  font-family: var(--serif);
  font-size: 20px;
}
.tag-hint {
  margin: 10px 0 14px;
  padding: 9px 12px;
  border-radius: 11px;
  background: color-mix(in srgb, var(--gold) 16%, var(--surface));
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}
.tag-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
  overflow: auto;
  max-height: 44vh;
}
.tag-row {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto 32px;
  align-items: center;
  gap: 10px;
  padding: 7px 10px 7px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--paper);
  transition: opacity 0.2s ease, border-color 0.2s ease;
}
.tag-row.removed {
  opacity: 0.52;
  border-style: dashed;
}
.tag-row.removed input {
  text-decoration: line-through;
}
.tag-row.fresh {
  border-color: #d9ab59;
}
.tag-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--terracotta);
}
.tag-row input {
  border: 0;
  background: transparent;
  font: inherit;
  font-size: 14px;
  color: var(--ink);
  padding: 3px 2px;
  min-width: 0;
}
.tag-row input:focus {
  outline: none;
  background: color-mix(in srgb, var(--terracotta) 9%, transparent);
  border-radius: 7px;
}
.tag-count {
  font-size: 11px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.tag-card .icon-button {
  width: 32px;
  height: 32px;
  padding: 6px;
  border-radius: 9px;
  background: transparent;
  color: var(--muted);
}
.tag-card .icon-button:hover {
  background: color-mix(in srgb, var(--ink) 9%, transparent);
  color: var(--terracotta);
}
.tag-card .icon-button svg {
  width: 16px;
  height: 16px;
}
.tag-add {
  display: flex;
  gap: 8px;
  margin: 12px 0 4px;
}
.tag-add input {
  flex: 1;
  min-width: 0;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--paper);
  color: var(--ink);
  font: inherit;
  font-size: 13px;
}
.tag-add input:focus {
  outline: none;
  border-color: var(--terracotta);
}
.tag-add .outline {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.tag-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.tag-error {
  margin: 0;
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: #b7553d;
}
.tag-actions {
  display: flex;
  gap: 8px;
}
@media (max-width: 560px) {
  .tag-layer {
    padding: 0;
    align-items: end;
  }
  .tag-card {
    width: 100%;
    max-height: 92dvh;
    border-radius: 22px 22px 0 0;
    padding: 18px 16px calc(14px + env(safe-area-inset-bottom));
  }
  .tag-rows {
    max-height: 38dvh;
  }
}
</style>
