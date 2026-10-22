<template>
  <span
    v-if="faces.length"
    class="member-stack"
    :class="{ 'has-more': moreCount > 0 }"
    :style="stackStyle"
    :title="tooltip"
    role="img"
    :aria-label="tooltip"
  >
    <span
      v-for="(face, index) in faces"
      :key="face.key"
      class="member-stack-face"
      :class="{ 'is-more': face.more }"
      :style="{
        zIndex: faces.length - index,
        background: face.more ? 'var(--surface)' : tone(face.user_id),
      }"
    >
      <img
        v-if="face.avatar && !broken[face.key]"
        :src="face.avatar"
        alt=""
        @error="broken[face.key] = true"
      />
      <template v-else>{{ face.label }}</template>
    </span>
  </span>
  <span
    v-else
    class="member-stack-fallback"
    :style="{ '--ms-size': `${size}px` }"
    >{{ letter }}</span
  >
</template>

<script setup>
import { computed, reactive } from 'vue'

const props = defineProps({
  members: { type: Array, default: () => [] },
  size: { type: Number, default: 30 },
  max: { type: Number, default: 3 },
  letter: { type: String, default: '圈' },
})

const broken = reactive({})

const shown = computed(() =>
  props.members.length > props.max
    ? props.members.slice(0, props.max - 1)
    : props.members,
)

const moreCount = computed(() =>
  props.members.length > props.max
    ? props.members.length - (props.max - 1)
    : 0,
)

const faces = computed(() => {
  const list = shown.value.map((member, index) => ({
    key: String(member.user_id ?? index),
    user_id: member.user_id ?? index,
    avatar: member.avatar || '',
    label: (member.nickname || member.username || '?').slice(0, 1),
    more: false,
  }))
  if (moreCount.value > 0) {
    list.push({
      key: 'more',
      user_id: -1,
      avatar: '',
      label: `+${moreCount.value}`,
      more: true,
    })
  }
  return list
})

const stackStyle = computed(() => {
  const overlap = Math.round(props.size * 0.3)
  return {
    '--ms-size': `${props.size}px`,
    '--ms-overlap': `${-overlap}px`,
    '--ms-font': `${Math.max(10, Math.round(props.size * 0.4))}px`,
  }
})

const tooltip = computed(() => {
  const names = props.members
    .slice(0, 6)
    .map((member) => member.nickname || member.username)
    .filter(Boolean)
  const head = names.join('、')
  const suffix = props.members.length > 6 ? ` 等 ${props.members.length} 人` : ''
  return head ? `圈内成员：${head}${suffix}` : '圈内成员'
})

const TONES = ['#d77e6b', '#5e8f91', '#c6a05a', '#7c9a7a']

function tone(id) {
  return TONES[Math.abs(Number(id) || 0) % TONES.length]
}
</script>

<style scoped>
.member-stack {
  display: inline-flex;
  align-items: center;
  flex: none;
  line-height: 1;
}
.member-stack-face {
  width: var(--ms-size);
  height: var(--ms-size);
  border-radius: 50%;
  display: grid;
  place-items: center;
  overflow: hidden;
  flex: none;
  color: #fff;
  font-family: var(--serif);
  font-size: var(--ms-font);
  font-weight: 700;
  border: 2px solid var(--ms-ring, var(--surface));
  box-sizing: border-box;
  background-clip: padding-box;
}
.member-stack-face + .member-stack-face {
  margin-left: var(--ms-overlap);
}
.member-stack-face img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.member-stack-face.is-more {
  color: var(--muted);
  font-family: inherit;
  font-size: calc(var(--ms-size) * 0.3);
  font-weight: 600;
  letter-spacing: -0.02em;
}
.member-stack-fallback {
  width: var(--ms-size);
  height: var(--ms-size);
  border-radius: 6px;
  background: #d7e5d6;
  color: var(--pine);
  display: grid;
  place-items: center;
  font-family: var(--serif);
  font-weight: 700;
  font-size: calc(var(--ms-size) * 0.55);
  flex: none;
}
</style>
