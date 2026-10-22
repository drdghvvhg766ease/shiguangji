<template>
  <section class="theme-studio" aria-label="主题装扮">
    <div class="section-head">
      <h2>预设主题</h2>
    </div>
    <p class="theme-hint">选一套喜欢的氛围，立即生效，并同步到你的账号。</p>
    <div class="preset-grid">
      <button
        v-for="p in presets"
        :key="p.key"
        type="button"
        class="preset-card"
        :class="{ active: theme.preset === p.key }"
        @click="pick(p.key)"
      >
        <span class="preset-dots">
          <i v-for="(c, i) in p.dots" :key="i" :style="{ background: c }" />
        </span>
        <strong>{{ p.label }}</strong>
        <small>{{ p.desc }}</small>
      </button>
    </div>

    <div class="section-head">
      <h2>自定义配色</h2>
    </div>
    <p class="theme-hint">
      自己动手调一套独一无二的配色，文字与辅助色会自动推导。
    </p>
    <div class="custom-grid">
      <label v-for="f in fields" :key="f.key" class="color-field">
        <input v-model="draft[f.key]" type="color" />
        <span>{{ f.label }}</span>
        <code>{{ draft[f.key] }}</code>
      </label>
    </div>
    <div class="custom-actions">
      <button class="outline" type="button" @click="resetDraft">重置拾色</button>
      <button
        class="primary"
        type="button"
        :disabled="saving"
        @click="saveCustom"
      >
        {{ saving ? '保存中…' : '应用并保存' }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { inject, reactive, ref } from 'vue'
import { CUSTOM_FIELDS, THEME_PRESETS, useThemeStore } from '../stores/theme'

const theme = useThemeStore()
const toast = inject('toast', () => {})
const presets = THEME_PRESETS
const fields = CUSTOM_FIELDS
const saving = ref(false)
const draft = reactive({})

function resetDraft() {
  for (const f of fields) {
    draft[f.key] = theme.custom?.[f.key] || f.fallback
  }
}
resetDraft()

async function pick(key) {
  await theme.selectPreset(key)
  toast(key === 'default' ? '已恢复默认主题' : '主题已切换并保存')
}
async function saveCustom() {
  saving.value = true
  try {
    await theme.saveCustom({ ...draft })
    toast('自定义配色已应用')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.theme-studio {
  padding-bottom: 24px;
}
.theme-hint {
  margin: -6px 0 14px;
  color: var(--muted);
  font-size: 12px;
}
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 8px;
}
.preset-card {
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 8px;
  padding: 12px;
  display: grid;
  gap: 5px;
  text-align: left;
  color: var(--ink);
}
.preset-card:hover {
  box-shadow: var(--shadow-sm);
}
.preset-card.active {
  border-color: var(--terracotta);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--terracotta) 25%, transparent);
}
.preset-card strong {
  font-size: 13px;
}
.preset-card small {
  color: var(--muted);
  font-size: 11px;
}
.preset-dots {
  display: flex;
  gap: 4px;
}
.preset-dots i {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.12);
}
.custom-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}
.color-field {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  padding: 8px 10px;
  font-size: 12px;
}
.color-field input[type='color'] {
  width: 30px;
  height: 30px;
  min-height: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.color-field span {
  flex: 1;
  font-weight: 700;
}
.color-field code {
  color: var(--muted);
  font-size: 10px;
}
.custom-actions {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
  margin-top: 14px;
}
@media (max-width: 650px) {
  .preset-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
