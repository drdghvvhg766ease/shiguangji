<template>
  <FootprintAtlas v-if="!picking" :posts="posts" :user-id="userId" @open-post="emit('open-post', $event)" />
  <div v-else class="footprint-tool">
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
    <div
      ref="canvas"
      class="footprint-map"
      :class="{ picking, 'is-empty': !picking && !located.length }"
      :aria-label="picking ? '点击地图选择地点' : '中国足迹地图'"
    >
      <div v-if="!picking && !located.length" class="map-hint">
        <span class="hint-compass"></span>
        <strong>足迹还是空的</strong>
        <em>走过的城市会在这张地图上连成一条线</em>
      </div>
    </div>
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
      <div class="empty-hint">
        <Compass :size="17" />
        <div>
          <strong>还没有足迹</strong>
          <p>发布或编辑旅行记录时添加地点，走过的城市就会在这里连成一条线。</p>
        </div>
      </div>
      <ul class="empty-steps">
        <li><i>1</i>打开任意一条旅行记录</li>
        <li><i>2</i>在详情页点「编辑地点」</li>
        <li><i>3</i>搜索城市名或在地图上点选</li>
      </ul>
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
import { ArrowUpRight, Compass, MapPin, Maximize2, X } from 'lucide-vue-next'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import CitySearch from './CitySearch.vue'
import FootprintAtlas from './FootprintAtlas.vue'
const props = defineProps({
  posts: { type: Array, default: () => [] },
  userId: { type: [Number, String], default: null },
  picking: Boolean,
  modelValue: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'open-post'])
const canvas = ref(null),
  error = ref(''),
  visitedProvinces = ref(new Set())
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
      maxBounds: [[0, 70], [56, 136]],
      maxBoundsViscosity: 0.6,
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
    base = L.geoJSON(data, {      style: (feature) => {
        const hit = visitedProvinces.value.has(feature.properties.name)
        return {
          color: hit ? '#a85540' : '#b9c4bb',
          weight: hit ? 1.6 : 0.9,
          fillColor: hit ? '#e0a184' : '#eef0e9',
          fillOpacity: hit ? 0.78 : 0.9,
        }
      },
      onEachFeature: (feature, layer) => {
        if (!feature.properties.name) return
        layer.bindTooltip(feature.properties.name, {
          sticky: true,
          className: 'province-tooltip',
        })
        layer.on({
          mouseover: () => {
            layer.setStyle({ weight: 1.8, color: '#3c6255', fillOpacity: 0.95 })
            layer.bringToFront()
          },
          mouseout: () => base.resetStyle(layer),
        })
      },
    }).addTo(map)
    base.bringToBack()
    fit()
    draw()
    syncHighlight()
  } catch (e) {
    if (e.name !== 'AbortError') error.value = '地图加载失败'
    return
  }
}
/** 射线法：点是否落在 GeoJSON 坐标环内（坐标为 [lng, lat]） */
function inRing(ring, lat, lng) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const yi = ring[i][1]
    const xi = ring[i][0]
    const yj = ring[j][1]
    const xj = ring[j][0]
    if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi)
      inside = !inside
  }
  return inside
}
/** 数组嵌套深度（到单个坐标点为止） */
function ringDepth(coords) {
  let n = 0
  let node = coords
  while (Array.isArray(node)) {
    n += 1
    node = node[0]
    if (n > 6) break
  }
  return n
}
/**
 * 判断点是否落在 GeoJSON 几何内（坐标为 [lng, lat]）。
 * 不硬编码 Polygon / MultiPolygon 的层数，而是探测到「坐标点」所在层，
 * 该层的上一层即环；对可能存在的洞（内环）做排除。
 */
function inGeometry(coords, lat, lng) {
  if (!Array.isArray(coords) || !coords.length) return false
  const d = ringDepth(coords)
  // depth 2: Polygon      coords[ring][point]
  // depth 3: MultiPolygon coords[polygon][ring][point]
  // depth 4: 更深嵌套    coords[a][b][ring][point]
  const ringAt = d <= 2 ? coords : d === 3 ? coords[0] : coords[0][0]
  if (!Array.isArray(ringAt) || !Array.isArray(ringAt[0])) return false
  if (!inRing(ringAt, lat, lng)) return false
  // 同层其余环视为洞
  const siblings = d <= 2 ? coords.slice(1) : (d === 3 ? ringAt : coords[0]).slice(1)
  return !siblings.some((hole) => inRing(hole, lat, lng))
}
/** 高亮已有足迹的省份 */
function markVisited() {
  if (!base) return
  const hit = new Set()
  if (located.value.length)
    base.eachLayer((layer) => {
      const feature = layer.feature
      const name = feature?.properties?.name
      if (!name || hit.has(name)) return
      if (
        located.value.some((p) =>
          inGeometry(feature.geometry?.coordinates, p.latitude, p.longitude),
        )
      )
        hit.add(name)
    })
  visitedProvinces.value = hit
  const visited = {
    color: '#a85540',
    weight: 1.6,
    fillColor: '#e0a184',
    fillOpacity: 0.78,
  }
  const plain = {
    color: '#b9c4bb',
    weight: 0.9,
    fillColor: '#eef0e9',
    fillOpacity: 0.9,
  }
  base.setStyle((f) => (hit.has(f.properties.name) ? visited : plain))
}
/** 渲染后统一补标，避免数据/图层就绪顺序不同导致漏标 */
function syncHighlight() {
  try {
    markVisited()
  } catch {
    visitedProvinces.value = new Set()
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
    const latlng = [p.latitude, p.longitude]
    if (!props.picking && points.length > 1) {
      // 途经点用细环标出，制造「旅程」层次
      L.circleMarker(latlng, {
        radius: 11,
        weight: 1,
        color: '#ad4737',
        fillColor: '#fff',
        fillOpacity: 0.5,
        opacity: 0.55,
        interactive: false,
      }).addTo(markers)
    }
    const marker = L.circleMarker(latlng, {
      radius: props.picking ? 9 : 7,
      weight: 2.4,
      color: '#fffdf8',
      fillColor: '#ad4737',
      fillOpacity: 1,
    }).addTo(markers)
    const label = document.createElement('span')
    label.textContent = `${p.location_name || '足迹'}${p.event_date ? ` · ${p.event_date}` : ''}`
    marker.bindTooltip(label)
    if (!props.picking) {
      marker.on('click', () => emit('open-post', { id: p.id }))
      if (points.length > 1) {
        const seq = L.marker(latlng, {
          interactive: false,
          icon: L.divIcon({
            className: 'footprint-seq',
            html: `<b>${i + 1}</b>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8],
          }),
        }).addTo(markers)
        seq.getElement()?.classList.add('is-first')
      }
    } else {
      L.circleMarker(latlng, {
        radius: 22,
        weight: 1.5,
        color: '#ad4737',
        fill: false,
        opacity: 0.5,
        interactive: false,
        className: 'pick-pulse',
      }).addTo(markers)
      marker.bindTooltip(label, { permanent: true, direction: 'top' })
    }
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
watch(
  () => [props.posts, props.modelValue],
  () => {
    draw()
    syncHighlight()
  },
  { deep: true },
)
// 足迹数量变化时补标（数据可能晚于图层到达）
watch(
  () => located.value.length,
  () => syncHighlight(),
)
onMounted(() => {
  if (props.picking) init()
})
onActivated(async () => {
  await nextTick()
  map?.invalidateSize()
  draw()
  syncHighlight()
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
