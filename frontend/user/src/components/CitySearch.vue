<template>
  <div
    ref="container"
    class="city-search"
    :class="{ 'opens-up': opensUp }"
    :style="{ '--city-results-height': `${resultsHeight}px` }"
    @focusout="leave"
  >
    <div class="city-search-field">
      <Search :size="16" aria-hidden="true" />
      <input
        ref="input"
        v-model="query"
        role="combobox"
        aria-label="搜索城市或省份"
        :aria-expanded="expanded"
        :aria-controls="listId"
        :aria-activedescendant="
          expanded && visible[highlighted]
            ? `${listId}-${visible[highlighted].code}`
            : undefined
        "
        autocomplete="off"
        placeholder="搜索城市或省份"
        @focus="showResults"
        @input="showResults"
        @keydown="keydown"
      />
      <button
        v-if="query"
        type="button"
        class="icon-button"
        title="清空搜索"
        aria-label="清空城市搜索"
        @click="clear"
      >
        <X :size="15" />
      </button>
    </div>
    <div v-if="expanded" class="city-search-popover">
      <p v-if="loading" class="city-search-status" role="status">城市加载中…</p>
      <div v-else-if="error" class="city-search-status" role="alert">
        {{ error
        }}<button type="button" class="text-button" @click="load">重试</button>
      </div>
      <template v-else>
        <div class="city-search-caption">
          {{ query.trim() ? `${matches.length} 个匹配地点` : '城市与地区' }}
        </div>
        <div
          :id="listId"
          ref="list"
          class="city-results"
          role="listbox"
          aria-label="城市搜索结果"
        >
          <button
            v-for="(city, i) in visible"
            :id="`${listId}-${city.code}`"
            :key="city.code"
            type="button"
            role="option"
            :aria-selected="modelValue?.location_name === city.name"
            :class="{ highlighted: highlighted === i }"
            tabindex="-1"
            @pointerdown.prevent
            @click="choose(city)"
          >
            <MapPin :size="15" />
            <span
              ><strong>{{ city.name }}</strong
              ><small>{{ city.province }}</small></span
            >
            <Check v-if="modelValue?.location_name === city.name" :size="15" />
          </button>
        </div>
        <p v-if="!matches.length" class="city-search-status" role="status">
          没有匹配城市
        </p>
        <button
          v-if="visible.length < matches.length"
          type="button"
          class="text-button city-more"
          @click="limit += 40"
        >
          显示更多
        </button>
      </template>
    </div>
  </div>
</template>
<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useId,
  watch,
} from 'vue'
import { Check, MapPin, Search, X } from 'lucide-vue-next'
const props = defineProps({ modelValue: { type: Object, default: null } })
const emit = defineEmits(['select'])
const listId = `cities-${useId()}`
const container = ref(null),
  opensUp = ref(false),
  resultsHeight = ref(240)
const query = ref(''),
  cities = ref([]),
  expanded = ref(false),
  highlighted = ref(-1)
const loading = ref(true),
  error = ref(''),
  limit = ref(40),
  input = ref(null),
  list = ref(null)
const matches = computed(() => {
  const terms = query.value.trim().split(/\s+/).filter(Boolean)
  return cities.value.filter((c) =>
    terms.every((term) => `${c.province} ${c.name}`.includes(term)),
  )
})
const visible = computed(() => matches.value.slice(0, limit.value))
let controller
let scrollParent
function position(ensureVisible = false) {
  if (!expanded.value || !container.value) return
  scrollParent = container.value.parentElement
  while (
    scrollParent &&
    !/(auto|scroll)/.test(getComputedStyle(scrollParent).overflowY)
  )
    scrollParent = scrollParent.parentElement
  const bounds = scrollParent?.getBoundingClientRect()
  const mobileNav = document
    .querySelector('.mobile-nav')
    ?.getBoundingClientRect()
  const bottom = Math.min(
    innerHeight,
    bounds?.bottom ?? innerHeight,
    mobileNav?.height ? mobileNav.top : innerHeight,
  )
  const top = Math.max(0, bounds?.top ?? 0)
  let rect = container.value.getBoundingClientRect()
  if (
    ensureVisible &&
    scrollParent &&
    (rect.bottom > bottom - 8 || rect.top < top + 8)
  ) {
    scrollParent.scrollTop +=
      rect.bottom > bottom - 8 ? rect.bottom - bottom + 8 : rect.top - top - 8
    rect = container.value.getBoundingClientRect()
  }
  const below = bottom - rect.bottom - 8,
    above = rect.top - top - 8
  opensUp.value = below < 260 && above > below
  resultsHeight.value = Math.max(
    52,
    Math.min(240, (opensUp.value ? above : below) - 88),
  )
}
function reposition(event) {
  if (event.type !== 'scroll' || event.target.contains?.(container.value))
    position(event.type === 'resize')
}
async function showResults() {
  expanded.value = true
  await nextTick()
  position(true)
}
async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/maps/china-cities.json', {
      signal: request.signal,
    })
    if (!response.ok) throw new Error()
    const data = await response.json()
    if (request !== controller) return
    cities.value = data.cities
  } catch (e) {
    if (e.name !== 'AbortError') error.value = '城市加载失败'
  } finally {
    if (request === controller) loading.value = false
  }
}
function choose(city) {
  emit('select', {
    location_name: city.name,
    latitude: city.latitude,
    longitude: city.longitude,
  })
  query.value = city.name
  expanded.value = false
  input.value?.focus()
  expanded.value = false
}
function clear() {
  query.value = ''
  input.value?.focus()
  expanded.value = true
}
function leave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) expanded.value = false
}
async function keydown(event) {
  if (event.isComposing) return
  if (event.key === 'Escape' && expanded.value) {
    event.preventDefault()
    event.stopPropagation()
    expanded.value = false
  } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    expanded.value = true
    const delta = event.key === 'ArrowDown' ? 1 : -1
    highlighted.value = Math.max(
      0,
      Math.min(visible.value.length - 1, highlighted.value + delta),
    )
    await nextTick()
    const target = list.value?.children[highlighted.value]
    if (target)
      list.value.scrollTo({
        top:
          target.offsetTop -
          list.value.offsetTop -
          list.value.clientHeight / 2 +
          target.clientHeight / 2,
      })
  } else if (event.key === 'Enter' && expanded.value) {
    event.preventDefault()
    const city = visible.value[highlighted.value >= 0 ? highlighted.value : 0]
    if (city) choose(city)
  } else if (event.key === 'Tab') expanded.value = false
}
watch(query, () => {
  highlighted.value = -1
  limit.value = 40
})
watch([expanded, query, loading], async () => {
  await nextTick()
  position(true)
})
watch(
  () => props.modelValue?.location_name,
  (name) => {
    if (!expanded.value) query.value = name || ''
  },
  { immediate: true },
)
onMounted(() => {
  load()
  window.addEventListener('resize', reposition)
  document.addEventListener('scroll', reposition, true)
})
onBeforeUnmount(() => {
  controller?.abort()
  window.removeEventListener('resize', reposition)
  document.removeEventListener('scroll', reposition, true)
})
</script>
