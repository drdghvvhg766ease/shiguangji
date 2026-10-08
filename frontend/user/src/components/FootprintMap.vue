<template>
  <div class="footprint-tool">
    <div class="map-toolbar">
      <span
        ><MapPin :size="16" />{{
          picking ? '记录地点' : `${located.length} 个足迹`
        }}</span
      >
      <div>
        <CitySearch
          v-if="picking"
          :model-value="modelValue"
          @select="chooseCity"
        />
        <button
          class="icon-button"
          type="button"
          title="查看全图"
          aria-label="查看全图"
          @click="fit"
        >
          <Maximize2 :size="17" />
        </button>
      </div>
    </div>
    <div ref="canvas" class="footprint-map" aria-label="中国足迹地图"></div>
    <p v-if="error" class="error-message">
      {{ error }}
      <button type="button" class="text-button" @click="init">重试</button>
    </p>
    <div v-if="picking" class="location-fields">
      <label
        >地点名称<input
          :value="modelValue?.location_name || ''"
          maxlength="128"
          placeholder="地点名称"
          @input="setName($event.target.value)" /></label
      ><label
        >纬度<input
          type="number"
          :value="modelValue?.latitude ?? ''"
          min="-90"
          max="90"
          step="any"
          @change="setCoordinate('latitude', $event.target.value)" /></label
      ><label
        >经度<input
          type="number"
          :value="modelValue?.longitude ?? ''"
          min="-180"
          max="180"
          step="any"
          @change="setCoordinate('longitude', $event.target.value)" /></label
      ><button
        type="button"
        class="text-button"
        :disabled="!modelValue"
        @click="emit('update:modelValue', null)"
      >
        <X :size="16" />清除地点
      </button>
    </div>
    <div v-else-if="!located.length" class="map-empty">
      还没有足迹，发布或编辑旅行记录时添加地点。
    </div>
    <div v-else class="footprint-list">
      <button
        v-for="(p, i) in located"
        :key="p.id"
        type="button"
        @click="focusPost(p)"
      >
        <span>{{ i + 1 }}</span>
        <div>
          <strong>{{ p.location_name || '旅行足迹' }}</strong
          ><small>{{ p.event_date }} · {{ p.nickname || p.username }}</small>
        </div>
        <ArrowUpRight :size="17" />
      </button>
    </div>
  </div>
</template>
<script setup>
import {
  computed,
  nextTick,
  onActivated,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'
import { ArrowUpRight, MapPin, Maximize2, X } from 'lucide-vue-next'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import CitySearch from './CitySearch.vue'
const props = defineProps({
  posts: { type: Array, default: () => [] },
  picking: Boolean,
  modelValue: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'open-post'])
const canvas = ref(null),
  error = ref('')
const located = computed(() =>
  props.posts
    .filter((p) => p.latitude != null && p.longitude != null)
    .slice()
    .sort((a, b) => a.event_date.localeCompare(b.event_date) || a.id - b.id),
)
let map,
  base,
  markers,
  resize,
  controller,
  dead = false
async function init() {
  error.value = ''
  controller?.abort()
  controller = new AbortController()
  if (!map) {
    map = L.map(canvas.value, {
      minZoom: 2,
      zoomSnap: 0.25,
      zoomDelta: 0.5,
      maxZoom: 12,
      zoomControl: true,
      attributionControl: false,
      scrollWheelZoom: false,
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false,
    }).setView([35, 105], 4)
    markers = L.layerGroup().addTo(map)
    map.on('click', (e) => {
      if (props.picking)
        emit('update:modelValue', {
          latitude: Number(e.latlng.lat.toFixed(5)),
          longitude: Number(e.latlng.lng.toFixed(5)),
          location_name: props.modelValue?.location_name || '旅行足迹',
        })
    })
    resize = new ResizeObserver(() => {
      if (canvas.value?.isConnected && canvas.value.clientWidth > 0) {
        map?.invalidateSize({ pan: false })
        if (base) fit()
      }
    })
    resize.observe(canvas.value)
  }
  try {
    const response = await fetch('/maps/china-provinces.json', {
      signal: controller.signal,
    })
    if (!response.ok) throw Error()
    const data = await response.json()
    if (dead) return
    base?.remove()
    base = L.geoJSON(data, {
      style: {
        color: '#aabbb0',
        weight: 1,
        fillColor: '#e8efea',
        fillOpacity: 1,
      },
      onEachFeature: (feature, layer) => {
        if (feature.properties.name)
          layer.bindTooltip(feature.properties.name, {
            sticky: true,
            className: 'province-tooltip',
          })
      },
    }).addTo(map)
    base.bringToBack()
    fit()
    draw()
  } catch (e) {
    if (e.name !== 'AbortError') error.value = '地图加载失败'
  }
}
function fit() {
  if (base) map.fitBounds(base.getBounds(), { padding: [12, 12] })
}
function draw() {
  if (!map) return
  markers.clearLayers()
  const points = props.picking
    ? props.modelValue?.latitude != null && props.modelValue?.longitude != null
      ? [props.modelValue]
      : []
    : located.value
  if (!props.picking && points.length > 1)
    L.polyline(
      points.map((p) => [p.latitude, p.longitude]),
      { color: '#ad4737', weight: 2, dashArray: '5 7', opacity: 0.7 },
    ).addTo(markers)
  points.forEach((p, i) => {
    const marker = L.circleMarker([p.latitude, p.longitude], {
      radius: 7,
      weight: 2,
      color: '#fff',
      fillColor: '#ad4737',
      fillOpacity: 1,
    }).addTo(markers)
    const label = document.createElement('span')
    label.textContent = `${p.location_name || '足迹'}${p.event_date ? ` · ${p.event_date}` : ''}`
    marker.bindTooltip(label)
    if (!props.picking)
      marker.on('click', () => emit('open-post', { id: p.id }))
    else marker.bindTooltip(label, { permanent: true, direction: 'top' })
  })
}
function chooseCity(location) {
  emit('update:modelValue', location)
  map?.setView([location.latitude, location.longitude], 6, { animate: false })
}
function setName(location_name) {
  if (props.modelValue)
    emit('update:modelValue', { ...props.modelValue, location_name })
}
function setCoordinate(key, value) {
  if (value === '') {
    emit('update:modelValue', null)
    return
  }
  const number = Number(value)
  if (
    !Number.isFinite(number) ||
    Math.abs(number) > (key === 'latitude' ? 90 : 180)
  )
    return
  emit('update:modelValue', {
    latitude: props.modelValue?.latitude ?? 35,
    longitude: props.modelValue?.longitude ?? 105,
    location_name: props.modelValue?.location_name || '旅行足迹',
    [key]: number,
  })
}
function focusPost(p) {
  map.setView([p.latitude, p.longitude], 6, { animate: false })
  emit('open-post', { id: p.id })
}
watch(() => [props.posts, props.modelValue], draw, { deep: true })
onMounted(init)
onActivated(async () => {
  await nextTick()
  map?.invalidateSize()
})
onBeforeUnmount(() => {
  dead = true
  controller?.abort()
  resize?.disconnect()
  map?.stop()
  map?.remove()
  map = null
})
</script>
