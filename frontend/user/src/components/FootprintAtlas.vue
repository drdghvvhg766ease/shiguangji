<template>
  <section
    class="footprint-atlas"
    :class="{ 'is-paused': !flowing || inactive }"
    :style="{ '--atlas-flow-duration': `${2.8 / speed}s` }"
    aria-label="中国旅行足迹"
  >
    <header class="atlas-heading">
      <div>
        <span class="atlas-eyebrow">EVERY STEP TELLS A STORY</span>
        <h2>山海有迹，步履不停。</h2>
        <p>把走过的路，珍藏成我们的中国地图。</p>
      </div>
      <dl class="atlas-stats">
        <div><dd>{{ cities.length }}<span>座</span></dd><dt>留下足迹的城市</dt></div>
        <div><dd>{{ visitedProvinces.size }}<span>个</span></dd><dt>走过的省级地区</dt></div>
        <div><dd>{{ memoryDays }}<span>天</span></dd><dt>收藏的旅行时光</dt></div>
      </dl>
    </header>

    <div class="atlas-workspace">
      <section class="atlas-map-panel" aria-label="足迹与轨迹">
        <div class="atlas-toolbar">
          <div class="atlas-tabs" role="group" aria-label="地图显示范围">
            <button type="button" :class="{ active: mode === 'all' }" :aria-pressed="mode === 'all'" @click="mode = 'all'">全部足迹</button>
            <button type="button" :class="{ active: mode === 'current' }" :aria-pressed="mode === 'current'" :disabled="!selectedJourney" @click="mode = 'current'">本月旅程</button>
          </div>
          <div class="atlas-animation-controls">
            <button type="button" class="atlas-flow-control" role="switch" :aria-checked="flowing" aria-label="轨迹流动动画" @click="flowing = !flowing"><i></i><span>轨迹流动</span></button>
            <button type="button" class="atlas-speed" :aria-label="`切换动画速度，当前${speed}倍速`" @click="speed = speed === 1 ? 2 : 1">{{ speed }}×</button>
          </div>
        </div>
        <div class="atlas-route-options">
          <div class="atlas-route-modes" role="group" aria-label="路线模式">
            <span>路线模式</span>
            <button type="button" :class="{ active: routeMode === 'timeline' }" :aria-pressed="routeMode === 'timeline'" @click="routeMode = 'timeline'">按日期连线</button>
            <button type="button" :class="{ active: routeMode === 'home' }" :aria-pressed="routeMode === 'home'" @click="useHomeMode"><Home :size="13" />从家出发</button>
          </div>
          <button v-if="routeMode === 'home'" type="button" class="atlas-home-setting" :aria-label="home ? `更改家的位置，当前${home.location_name}` : '设置家的位置'" @click="openHomeEditor"><MapPin :size="12" /><span>{{ home?.location_name || '设置家的位置' }}</span><ChevronRight :size="12" /></button>
        </div>
        <p v-if="homeStorageError && routeMode === 'home'" class="atlas-home-storage" role="status">{{ homeStorageError }}</p>
        <div class="footprint-map atlas-map" :aria-busy="loading">
          <svg ref="mapSvg" class="atlas-svg" :viewBox="viewBox" aria-label="包含省界、城市标记和旅行连线的中国足迹地图" @pointerdown="startPan" @pointermove="movePan" @pointerup="endPan" @pointercancel="endPan">
            <defs>
              <path :id="`${instanceId}-plane`" d="M12 0 3-2-3-10-6-10-3-2-9-2-12-5-14-5-11 0-14 5-12 5-9 2-3 2-6 10-3 10 3 2Z" />
              <clipPath :id="`${instanceId}-inset`"><rect x="932" y="441" width="101" height="114" rx="2" /></clipPath>
              <clipPath :id="`${instanceId}-map-clip`"><rect x="0" y="0" width="1080" height="600" /></clipPath>
            </defs>
            <path class="atlas-grid" d="M78 116h923M50 214h946M62 312h895M128 410h886M170 508h821M191 70v460M364 67v470M537 50v492M710 55v489M883 67v472" />
            <g transform="translate(56,57)" class="atlas-compass"><text y="-15" text-anchor="middle">N</text><path d="M0-7 5 13 0 9-5 13Z" /><path d="M0 9v15" fill="none" stroke="currentColor" /></g>
            <g :clip-path="`url(#${instanceId}-map-clip)`">
              <g :transform="`translate(${pan.x} ${pan.y}) translate(535 287) scale(${zoom}) translate(-535 -287)`" class="atlas-scene">
                <g class="atlas-provinces">
                  <path v-for="province in provinces" :key="province.code" :d="province.path" fill-rule="evenodd" class="atlas-province" :class="{ visited: visitedProvinces.has(province.code), selected: selectedProvinces.has(province.code), 'boundary-mark': !province.name }"><title>{{ province.name || '海域界线' }}</title></path>
                </g>
                <g class="atlas-province-labels"><text v-for="province in labeledProvinces" :key="province.code" :x="province.label[0]" :y="province.label[1]">{{ province.shortName }}</text></g>
                <g v-for="(route, routeIndex) in routes" :key="`${routeMode}-${route.id}`" class="atlas-route" :class="{ selected: route.selected }" :data-post-ids="route.postIds?.join(',')">
                  <path :id="`${instanceId}-route-${route.id}`" :d="route.path" class="atlas-route-base" />
                  <path :d="route.path" class="atlas-route-flow" />
                  <g :key="`${route.id}-${speed}`" class="atlas-plane" aria-hidden="true">
                    <g class="atlas-plane-icon"><use :href="`#${instanceId}-plane`" class="atlas-plane-shape" /></g>
                    <animateMotion :dur="`${7 / speed}s`" :begin="`${-(routeIndex % 5) * .8 / speed}s`" rotate="auto" repeatCount="indefinite" calcMode="paced"><mpath :href="`#${instanceId}-route-${route.id}`" /></animateMotion>
                  </g>
                </g>
                <g v-for="city in mapCities" :key="city.key" class="atlas-city" :class="{ selected: city.posts.some(post => selectedIds.has(post.id)), active: city.posts.some(post => post.id === selectedPost?.id) }" :transform="`translate(${city.point[0]} ${city.point[1]})`" role="button" tabindex="0" :aria-label="`查看${city.name}的足迹，${city.posts.length}条记录`" @click.stop="selectCity(city)" @keydown.enter.prevent="selectCity(city)" @keydown.space.prevent="selectCity(city)">
                  <circle r="19" class="atlas-city-hit" /><circle r="9" class="atlas-city-pulse" /><circle r="10" class="atlas-city-ring" /><circle r="4.8" class="atlas-city-core" />
                  <text :x="city.label.x" :y="city.label.y" :text-anchor="city.label.anchor">{{ city.name }}</text>
                </g>
                <g v-if="routeMode === 'home' && homePoint" class="atlas-home-marker" :transform="`translate(${homePoint[0]} ${homePoint[1]})`" role="button" tabindex="0" :aria-label="`家：${home.location_name}，点击更改出发地点`" @click.stop="openHomeEditor" @keydown.enter.prevent="openHomeEditor" @keydown.space.prevent="openHomeEditor">
                  <circle r="22" class="atlas-home-hit" /><circle r="17" class="atlas-home-halo" /><circle r="11" class="atlas-home-core" /><path d="M-6 0 0-5 6 0M-4-1v6h3V2h2v3h3v-6" class="atlas-home-icon" /><text :x="homePoint[0] > 790 ? -22 : 22" y="-17" :text-anchor="homePoint[0] > 790 ? 'end' : 'start'">家 · {{ home.location_name }}</text>
                </g>
              </g>
            </g>
            <g v-if="features.length" class="atlas-inset"><rect x="928" y="435" width="108" height="144" rx="3" /><g :clip-path="`url(#${instanceId}-inset)`"><path v-for="province in provinces" :key="province.code" :d="province.insetPath" :class="{ 'boundary-mark': !province.name }" fill-rule="evenodd" /></g><text x="982" y="569" text-anchor="middle">南海诸岛</text></g>
          </svg>
          <div class="atlas-zoom" aria-label="地图缩放"><button type="button" aria-label="放大地图" @click="zoom = Math.min(2.5, zoom + .25)"><Plus :size="16" /></button><button type="button" aria-label="缩小地图" @click="zoom = Math.max(1, zoom - .25)"><Minus :size="16" /></button><button type="button" aria-label="查看全图" @click="resetMap"><Maximize2 :size="14" /></button></div>
          <div class="atlas-map-note"><Mountain :size="20" /><span><strong>山川为序，足迹为章</strong><small>点击城市重温记忆 · 拖动地图探索</small></span></div>
          <div v-if="loading" class="atlas-status" role="status">正在展开山海地图…</div>
          <div v-else-if="error" class="atlas-status" role="alert"><strong>{{ error }}</strong><button type="button" @click="loadMap">重新加载</button></div>
          <div v-else-if="!located.length" class="atlas-status atlas-empty"><Compass :size="25" /><strong>第一枚足迹，等你抵达。</strong><span>发布或编辑记录时添加地点，走过的城市就会出现在这里。</span></div>
          <div v-else-if="routeMode === 'home' && !home" class="atlas-status atlas-home-prompt"><Home :size="25" /><strong>每一次远行，都从家出发。</strong><span>设置家的位置，看看它与各个目的地的连线。</span><button type="button" @click="openHomeEditor">设置家的位置</button></div>
        </div>
        <div class="atlas-legend"><span><i class="legend-province"></i>走过的省份</span><span><i class="legend-city"></i>城市足迹</span><span><Plane :size="12" />飞行轨迹</span><small>{{ routeMode === 'home' ? '从家分别飞向目的地' : '按记录日期连线' }}</small></div>
      </section>

      <aside class="atlas-journey-panel" aria-label="旅程与旅行记录">
        <div class="atlas-journey-header"><strong>一程一故事</strong><span>{{ journeyPosition }}</span></div>
        <div class="atlas-art"><svg viewBox="0 0 600 285" preserveAspectRatio="xMidYMid slice" aria-label="层叠青山与日落插画"><rect width="600" height="285" fill="#e5e9d9" /><circle cx="447" cy="87" r="33" fill="#c9805d" /><path d="M0 190 79 150 117 167 189 82 222 116 249 95 331 190 390 147 458 173 533 113 600 147V285H0Z" fill="#bbc6ac" /><path d="m131 143 58-61 32 34 26-20 33 40-32-17-14 17-34-34-21 27-15-8Z" fill="#eff0e0" /><path d="M0 223 91 193 165 207 263 155 353 225 423 188 502 211 600 179V285H0Z" fill="#8ea387" /><path d="M0 254c82-41 138-8 203-22s120-7 180 10 135-2 217-25v68H0Z" fill="#5e7e67" /><path d="M318 245c-29 9-33 19-21 40h18c-15-19-10-28 17-40Z" fill="#d6cfb6" /><path d="M0 275c108-31 157-20 250-9s181-13 350-8M0 266c105-31 160-20 250-13s185-13 350-10" fill="none" stroke="#bdcbb0" opacity=".45" /></svg><span>INTO THE MOUNTAINS</span></div>
        <div class="atlas-journey-summary"><span class="atlas-month-tag">按月收藏</span><h3>{{ selectedJourney?.name || '我们的山海行记' }}</h3><p>{{ journeySummary }}</p><div><span><CalendarDays :size="12" />{{ journeyDates }}</span><span><MapPin :size="12" />{{ selectedJourney?.posts.length || 0 }} 枚足迹</span></div></div>
        <div v-if="selectedJourney" class="footprint-list atlas-timeline" aria-label="本月足迹记录">
          <button v-for="post in selectedJourney.posts" :key="post.id" type="button" :class="{ active: selectedPost?.id === post.id }" :aria-pressed="selectedPost?.id === post.id" @click="selectedPostId = post.id"><span class="atlas-timeline-dot"></span><div><strong>{{ post.location_name || '旅行足迹' }}</strong><small>{{ excerpt(post) }}</small></div><time :datetime="post.event_date">{{ shortDate(post.event_date) }}</time></button>
        </div>
        <div v-else class="atlas-no-journey"><MapPin :size="18" /><p>去记录里添加一个地点，<br>从此让回忆有迹可循。</p></div>
        <div v-if="selectedPost" class="atlas-memory-detail"><div><span>{{ selectedPost.nickname || selectedPost.username || '旅行者' }} · {{ selectedPost.event_date }}</span><strong>{{ selectedPost.location_name || '旅行足迹' }}</strong><p>{{ excerpt(selectedPost) }}</p></div><button type="button" @click="emit('open-post', { id: selectedPost.id })">打开这段回忆<ArrowUpRight :size="14" /></button></div>
        <div class="atlas-journey-footer">一路风景，值得慢慢收藏。<Leaf :size="14" /></div>
      </aside>
    </div>

    <section v-if="journeys.length" class="atlas-journey-strip" aria-label="月份旅程切换"><div><strong>下一段故事，仍在路上。</strong><small>THE JOURNEY IS THE DESTINATION</small></div><div class="atlas-journey-cards"><button v-for="(journey, index) in journeys" :key="journey.id" type="button" :class="{ active: selectedJourney?.id === journey.id }" :aria-pressed="selectedJourney?.id === journey.id" @click="selectJourney(journey.id)"><span class="atlas-card-icon"><Mountain :size="20" /></span><span><strong>{{ journey.name }}</strong><small>{{ journey.posts.length }} 枚足迹 · {{ journeyCities(journey) }} 个地点</small></span><em>{{ String(index + 1).padStart(2, '0') }}</em></button></div></section>
    <dialog ref="homeDialog" class="atlas-home-dialog" :aria-labelledby="`${instanceId}-home-title`" @cancel.prevent="closeHomeEditor">
      <form @submit.prevent="saveHome">
        <header><div><span>HOME IS WHERE THE JOURNEY BEGINS</span><h3 :id="`${instanceId}-home-title`">从家出发，去看山海。</h3></div><button type="button" class="atlas-dialog-close" aria-label="关闭家的位置设置" @click="closeHomeEditor"><X :size="20" /></button></header>
        <p>搜索所在城市，也可以填写家的精确经纬度。</p>
        <CitySearch v-if="homeEditorOpen" :model-value="draftHome" @select="chooseHomeCity" />
        <label class="atlas-home-field">家的地点名称<input v-model="draftHome.location_name" maxlength="128" placeholder="例如：广州 · 我的家" required /></label>
        <div class="atlas-home-coordinates"><label class="atlas-home-field">家的纬度<input v-model="draftHome.latitude" type="number" min="-90" max="90" step="any" required /></label><label class="atlas-home-field">家的经度<input v-model="draftHome.longitude" type="number" min="-180" max="180" step="any" required /></label></div>
        <p v-if="homeError" class="atlas-home-error" role="alert">{{ homeError }}</p>
        <footer><button v-if="home" type="button" class="atlas-home-remove" @click="clearHome">清除家的位置</button><button type="button" class="atlas-home-cancel" @click="closeHomeEditor">取消</button><button type="submit" class="atlas-home-save"><Home :size="14" />保存出发地点</button></footer>
        <small>家的位置按账号保存在当前浏览器，刷新后可继续使用。</small>
      </form>
    </dialog>
  </section>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, useId, watch } from 'vue'
import { ArrowUpRight, CalendarDays, ChevronRight, Compass, Home, Leaf, MapPin, Maximize2, Minus, Mountain, Plane, Plus, X } from 'lucide-vue-next'
import CitySearch from './CitySearch.vue'
import { createChinaProjection, geometryPath, groupJourneys, homeRoutes, journeyPath, locatedPosts, locationKey, normalizeHomeLocation, pointInGeometry } from '../utils/footprints'

const props = defineProps({
  posts: { type: Array, default: () => [] },
  userId: { type: [Number, String], default: null },
})
const emit = defineEmits(['open-post'])
const instanceId = `atlas-${useId()}`
const mapSvg = ref(null)
const features = ref([])
const loading = ref(true)
const error = ref('')
const selectedJourneyId = ref('')
const selectedPostId = ref(null)
const mode = ref('all')
const routeMode = ref('timeline')
const home = ref(null)
const homeDialog = ref(null)
const homeEditorOpen = ref(false)
const draftHome = ref({ location_name: '', latitude: '', longitude: '' })
const homeError = ref('')
const homeStorageError = ref('')
const homeStorageKey = computed(() => `shiguangji-footprint-home-${props.userId ?? 'guest'}`)
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const speed = ref(1)
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
const compactViewport = window.matchMedia('(max-width: 650px)')
const flowing = ref(!motionPreference.matches)
const compact = ref(compactViewport.matches)
const inactive = ref(false)
const viewBox = computed(() => compact.value ? '0 -40 1080 710' : '0 0 1080 600')
const located = computed(() => locatedPosts(props.posts))
const journeys = computed(() => groupJourneys(located.value))
const selectedJourney = computed(() => journeys.value.find(journey => journey.id === selectedJourneyId.value) || journeys.value[0])
const selectedIds = computed(() => new Set(selectedJourney.value?.posts.map(post => post.id) || []))
const selectedPost = computed(() => selectedJourney.value?.posts.find(post => post.id === selectedPostId.value) || selectedJourney.value?.posts.at(-1))
const project = computed(() => createChinaProjection(features.value, routeMode.value === 'home' && home.value ? [...located.value, home.value] : located.value))
const homePoint = computed(() => home.value ? project.value([home.value.longitude, home.value.latitude]) : null)
const memoryDays = computed(() => new Set(located.value.map(post => post.event_date).filter(Boolean)).size)
const provinces = computed(() => features.value.map(feature => ({
  code: feature.properties.adcode,
  name: feature.properties.name,
  shortName: (feature.properties.name || '').replace(/省|市|自治区|维吾尔|回族|壮族|特别行政区/g, ''),
  label: project.value(feature.properties.centroid || feature.properties.center || [105, 36]),
  path: geometryPath(feature.geometry, project.value, true),
  insetPath: geometryPath(feature.geometry, ([longitude, latitude]) => [930 + (longitude - 105) * 5.3, 433 + (24 - latitude) * 5.7]),
})))
const labeledProvinces = computed(() => provinces.value.filter(province => province.name && ![110000, 120000, 310000, 320000, 330000, 440000, 810000, 820000].includes(province.code)))
const provincePosts = computed(() => new Map(features.value.filter(feature => feature.properties.name).map(feature => [feature.properties.adcode, located.value.filter(post => pointInGeometry(feature.geometry, [Number(post.longitude), Number(post.latitude)]))])))
const visitedProvinces = computed(() => new Set([...provincePosts.value].filter(([, posts]) => posts.length).map(([code]) => code)))
const selectedProvinces = computed(() => new Set([...provincePosts.value].filter(([, posts]) => posts.some(post => selectedIds.value.has(post.id))).map(([code]) => code)))
const displayedPosts = computed(() => mode.value === 'all' ? located.value : selectedJourney.value?.posts || [])
const routes = computed(() => {
  if (routeMode.value === 'home') {
    return homeRoutes(home.value, displayedPosts.value, project.value).map(route => ({ ...route, selected: route.postIds.some(id => selectedIds.value.has(id)) }))
  }
  return (mode.value === 'current' ? [selectedJourney.value].filter(Boolean) : journeys.value)
    .map(journey => ({ id: journey.id, path: journeyPath(journey.posts, project.value), selected: journey.id === selectedJourney.value?.id }))
    .filter(route => route.path)
})
const cities = computed(() => {
  const grouped = new Map()
  located.value.forEach(post => {
    const key = locationKey(post)
    if (!grouped.has(key)) grouped.set(key, { key, name: post.location_name || '旅行足迹', coordinate: [Number(post.longitude), Number(post.latitude)], posts: [] })
    const city = grouped.get(key)
    city.name = post.location_name || city.name
    city.posts.push(post)
  })
  const positioned = [...grouped.values()].map(city => ({ ...city, point: project.value(city.coordinate) }))
  positioned.forEach((city, index) => {
    const nearby = positioned.filter(other => other !== city && Math.hypot(other.point[0] - city.point[0], other.point[1] - city.point[1]) < 55)
    const left = city.point[0] < 720 || index % 2 === 0
    city.label = { x: left ? -14 : 14, y: nearby.length ? (index % 2 ? 28 : -20) : -16, anchor: left ? 'end' : 'start' }
  })
  return positioned
})
const visibleCities = computed(() => mode.value === 'all' ? cities.value : cities.value.filter(city => city.posts.some(post => selectedIds.value.has(post.id))))
const mapCities = computed(() => routeMode.value === 'home' && home.value ? visibleCities.value.filter(city => city.key !== locationKey(home.value)) : visibleCities.value)
const journeyPosition = computed(() => selectedJourney.value ? `${String(journeys.value.indexOf(selectedJourney.value) + 1).padStart(2, '0')} / ${String(journeys.value.length).padStart(2, '0')}` : '等待出发')
const journeySummary = computed(() => {
  if (!selectedJourney.value) return '每一段日常，也可以是一次出发。'
  if (routeMode.value === 'home' && home.value) return `从${home.value.location_name}出发，重温这个月的远行。`
  const names = [...new Set(selectedJourney.value.posts.map(post => post.location_name || '旅行足迹'))]
  return names.length > 1 ? `从${names[0]}，到${names.at(-1)}。` : `在${names[0]}，收藏生活里的风景。`
})
const journeyDates = computed(() => selectedJourney.value ? `${shortDate(selectedJourney.value.posts[0].event_date)} — ${shortDate(selectedJourney.value.posts.at(-1).event_date)}` : '待记录')
let controller
let disposed = false
let drag
let dragged = false

function shortDate(value) {
  return value?.slice(5).replace('-', '.') || '未标日期'
}

async function openHomeEditor() {
  draftHome.value = home.value ? { ...home.value } : { location_name: '', latitude: '', longitude: '' }
  homeError.value = ''
  homeEditorOpen.value = true
  await nextTick()
  if (!homeDialog.value?.open) homeDialog.value?.showModal()
}

function closeHomeEditor() {
  homeDialog.value?.close()
  homeEditorOpen.value = false
}

function useHomeMode() {
  routeMode.value = 'home'
  if (!home.value) openHomeEditor()
}

function chooseHomeCity(location) {
  draftHome.value = { ...location }
  homeError.value = ''
}

function saveHome() {
  const location = normalizeHomeLocation(draftHome.value)
  if (!location) {
    homeError.value = '请填写地点名称和有效的经纬度。'
    return
  }
  home.value = location
  homeStorageError.value = ''
  try {
    localStorage.setItem(homeStorageKey.value, JSON.stringify(location))
  } catch {
    homeStorageError.value = '当前浏览器无法保存家的位置，刷新后需要重新设置。'
  }
  closeHomeEditor()
  resetMap()
}

function clearHome() {
  home.value = null
  homeStorageError.value = ''
  try {
    localStorage.removeItem(homeStorageKey.value)
  } catch {
    homeStorageError.value = '当前浏览器无法保存这次更改，刷新后请再次检查家的位置。'
  }
  closeHomeEditor()
}

function excerpt(post) {
  return post.content?.trim().slice(0, 70) || `${post.nickname || post.username || '我们'}留在这里的一段回忆。`
}

function journeyCities(journey) {
  return new Set(journey.posts.map(post => `${Number(post.latitude).toFixed(3)},${Number(post.longitude).toFixed(3)}`)).size
}

function selectJourney(id) {
  selectedJourneyId.value = id
  selectedPostId.value = null
}

function selectCity(city) {
  if (dragged) return
  const post = city.posts.filter(entry => selectedIds.value.has(entry.id)).at(-1) || city.posts.at(-1)
  selectedJourneyId.value = post.event_date?.slice(0, 7) || 'undated'
  selectedPostId.value = post.id
}

function resetMap() {
  zoom.value = 1
  pan.value = { x: 0, y: 0 }
}

function svgPoint(event) {
  return new DOMPoint(event.clientX, event.clientY).matrixTransform(mapSvg.value.getScreenCTM().inverse())
}

function startPan(event) {
  if (event.button !== 0 || event.target.closest('[role="button"]')) return
  drag = { point: svgPoint(event), pan: { ...pan.value }, id: event.pointerId }
  dragged = false
  mapSvg.value.setPointerCapture(event.pointerId)
}

function movePan(event) {
  if (!drag || event.pointerId !== drag.id) return
  const point = svgPoint(event)
  const deltaX = point.x - drag.point.x
  const deltaY = point.y - drag.point.y
  if (Math.hypot(deltaX, deltaY) > 5) dragged = true
  pan.value = { x: Math.max(-500, Math.min(500, drag.pan.x + deltaX)), y: Math.max(-300, Math.min(300, drag.pan.y + deltaY)) }
}

function endPan(event) {
  if (!drag || event.pointerId !== drag.id) return
  if (mapSvg.value.hasPointerCapture(event.pointerId)) mapSvg.value.releasePointerCapture(event.pointerId)
  drag = null
  dragged = false
}

async function syncAnimation() {
  await nextTick()
  if (flowing.value && !inactive.value) mapSvg.value?.unpauseAnimations()
  else mapSvg.value?.pauseAnimations()
}

function syncPreference() {
  flowing.value = !motionPreference.matches
}

function syncViewport() {
  compact.value = compactViewport.matches
}

async function loadMap() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/maps/china-provinces.json', { signal: request.signal })
    if (!response.ok) throw new Error()
    const data = await response.json()
    if (!disposed && controller === request) features.value = data.features
  } catch (failure) {
    if (failure.name !== 'AbortError' && !disposed) error.value = '地图加载失败，请再试一次。'
  } finally {
    if (!disposed && controller === request) loading.value = false
  }
}

watch(homeStorageKey, () => {
  closeHomeEditor()
  homeStorageError.value = ''
  try {
    home.value = normalizeHomeLocation(JSON.parse(localStorage.getItem(homeStorageKey.value) || 'null'))
  } catch {
    home.value = null
  }
}, { immediate: true })
watch([flowing, speed, routes], syncAnimation, { flush: 'post' })
watch(located, () => {
  if (!journeys.value.some(journey => journey.id === selectedJourneyId.value)) selectJourney(journeys.value[0]?.id || '')
})
onMounted(() => {
  loadMap()
  syncAnimation()
  motionPreference.addEventListener('change', syncPreference)
  compactViewport.addEventListener('change', syncViewport)
})
onActivated(() => { inactive.value = false; syncAnimation() })
onDeactivated(() => { inactive.value = true; mapSvg.value?.pauseAnimations(); closeHomeEditor() })
onBeforeUnmount(() => {
  disposed = true
  controller?.abort()
  closeHomeEditor()
  motionPreference.removeEventListener('change', syncPreference)
  compactViewport.removeEventListener('change', syncViewport)
})
</script>

<style scoped>
.footprint-atlas { --atlas-paper:#f6f4ec; --atlas-panel:#fbfaf5; --atlas-ink:#26483e; --atlas-muted:#819078; --atlas-line:#dfe4d5; --atlas-orange:#bc6848; color:var(--atlas-ink); margin:6px 0 24px; }
.footprint-atlas button { min-height:0; color:inherit; }
.atlas-heading { display:flex; align-items:center; justify-content:space-between; gap:24px; padding:16px 0 26px; }
.atlas-eyebrow { display:flex; align-items:center; gap:10px; font-size:9px; color:#87947e; letter-spacing:2.5px !important; }
.atlas-eyebrow::before { content:''; width:20px; height:1px; background:var(--atlas-orange); }
.atlas-heading h2 { font-family:var(--serif); font-size:35px; line-height:1.4; font-weight:500; margin:9px 0 8px; }
.atlas-heading p { font-size:11px; color:var(--atlas-muted); margin:0; }
.atlas-stats { display:flex; flex-shrink:0; gap:28px; margin:0; }
.atlas-stats > div { position:relative; }
.atlas-stats > div + div::before { content:''; position:absolute; left:-15px; top:7px; height:38px; border-left:1px solid var(--atlas-line); }
.atlas-stats dd { font:38px/1.2 Georgia,serif; margin:0 0 7px; }
.atlas-stats dd span { font-size:10px; color:#9ba58f; margin-left:5px; }
.atlas-stats dt { color:#88947f; font-size:9px; }
.atlas-workspace { display:grid; grid-template-columns:minmax(0,1fr) 294px; gap:20px; align-items:stretch; }
.atlas-map-panel,.atlas-journey-panel { min-width:0; border:1px solid var(--atlas-line); border-radius:13px; background:var(--atlas-panel); overflow:hidden; }
.atlas-map-panel { display:flex; flex-direction:column; }
.atlas-map-panel > .atlas-toolbar,.atlas-map-panel > .atlas-legend { flex-shrink:0; }
.atlas-map-panel > .atlas-route-options { flex-shrink:0; }
.atlas-route-options { min-height:48px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px 12px; padding:10px 21px; border-bottom:1px solid var(--atlas-line); background:#f7f8f0; }
.atlas-route-modes { display:flex; align-items:center; gap:6px; }
.atlas-route-modes > span { font-size:9px; color:#98a189; margin-right:5px; white-space:nowrap; }
.atlas-route-modes > button { display:flex; align-items:center; gap:5px; border:1px solid transparent; border-radius:5px; background:none; color:#8b977e; padding:5px 9px; font-size:10px; white-space:nowrap; }
.atlas-route-modes > button.active { background:#e8edde; color:#536e4c; border-color:#d5dfc7; }
.atlas-home-setting { display:flex; align-items:center; gap:5px; min-width:0; max-width:200px; padding:4px 0; border:0; background:none; color:#768866 !important; font-size:10px; }
.atlas-home-setting span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.atlas-home-storage { margin:0; padding:8px 21px; font-size:10px; color:#997154; background:#f7f0e4; }
.atlas-toolbar { height:60px; padding:0 21px; display:flex; align-items:center; justify-content:space-between; gap:12px; border-bottom:1px solid var(--atlas-line); }
.atlas-tabs { display:flex; gap:4px; padding:4px; border-radius:6px; background:#eef0e5; }
.atlas-tabs button { padding:7px 12px; border:0; border-radius:4px; background:transparent; color:#8d987f; font-size:10px; white-space:nowrap; }
.atlas-tabs button.active { background:#fffef8; color:var(--atlas-ink); box-shadow:0 1px 4px #29402c08; font-weight:600; }
.atlas-animation-controls { display:flex; align-items:center; gap:10px; }
.atlas-flow-control { display:flex; align-items:center; gap:7px; padding:0; border:0; background:none; color:#819176 !important; font-size:10px; white-space:nowrap; }
.atlas-flow-control i { position:relative; width:29px; height:16px; border-radius:20px; background:var(--atlas-ink); }
.atlas-flow-control i::after { content:''; position:absolute; left:16px; top:3px; width:10px; height:10px; border-radius:50%; background:#fffdf2; transition:left .2s; }
.atlas-flow-control[aria-checked='false'] i { background:#c2cbb7; }
.atlas-flow-control[aria-checked='false'] i::after { left:3px; }
.atlas-speed { font:11px Georgia,serif; border:1px solid var(--atlas-line); border-radius:4px; background:none; padding:4px 5px; }
.footprint-map.atlas-map { flex:1 0 auto; height:clamp(440px,51vh,640px); border:0; border-radius:0; box-shadow:none; background:radial-gradient(ellipse at 48% 42%,#f0f3e8 0%,#fbfaf5 75%); isolation:isolate; }
.atlas-map::after { display:none; }
.atlas-svg { display:block; width:100%; height:100%; cursor:grab; touch-action:none; }
.atlas-svg:active { cursor:grabbing; }
.atlas-grid { fill:none; stroke:#dce2d5; stroke-width:.7; stroke-dasharray:1 7; opacity:.5; }
.atlas-compass { color:#8b9c7c; fill:currentColor; }
.atlas-compass text { font:9px Georgia,serif; }
.atlas-province { fill:#e6e9dd; stroke:#fafaf1; stroke-width:1.1; stroke-linejoin:round; transition:fill .25s; }
.atlas-province.visited { fill:#abbba0; }
.atlas-province.selected { fill:#99af91; }
.atlas-province.boundary-mark { fill:#b9c4af; stroke:none; }
.atlas-province-labels text { text-anchor:middle; fill:#96a18b; font-size:10px; pointer-events:none; }
.atlas-route { opacity:.72; }
.atlas-route.selected { opacity:1; }
.atlas-route-base { fill:none; stroke:#61856e; stroke-width:1.6; opacity:.4; }
.atlas-route-flow { fill:none; stroke:#61856e; stroke-width:1.8; stroke-linecap:round; stroke-dasharray:2 13; animation:atlas-flow var(--atlas-flow-duration) linear infinite; }
.atlas-route.selected .atlas-route-base { stroke:var(--atlas-orange); stroke-width:2; opacity:.35; }
.atlas-route.selected .atlas-route-flow { stroke:var(--atlas-orange); stroke-width:2.3; }
.atlas-plane { color:#75906b; pointer-events:none; }
.atlas-route.selected .atlas-plane { color:var(--atlas-orange); }
.atlas-plane-shape { fill:currentColor; stroke:#fffaf0; stroke-width:1.4; stroke-linejoin:round; paint-order:stroke; }
.atlas-home-marker { cursor:pointer; outline:none; }
.atlas-home-hit { fill:transparent; }
.atlas-home-halo { fill:#78926d; fill-opacity:.13; stroke:#8ea57e; stroke-width:.8; }
.atlas-home-core { fill:#426951; stroke:#fffdf0; stroke-width:2; }
.atlas-home-icon { fill:none; stroke:#fffdf0; stroke-width:1.3; stroke-linecap:round; stroke-linejoin:round; }
.atlas-home-marker text { font-size:12px; fill:#426951; font-weight:600; paint-order:stroke; stroke:#f6f7ef; stroke-width:3.5; stroke-linejoin:round; }
.atlas-home-marker:hover .atlas-home-halo,.atlas-home-marker:focus-visible .atlas-home-halo { stroke:#3b6445; stroke-width:2; }
.atlas-city { cursor:pointer; outline:none; }
.atlas-city-hit { fill:transparent; }
.atlas-city-pulse { fill:#cf9879; opacity:0; pointer-events:none; }
.atlas-city.selected .atlas-city-pulse { transform-box:fill-box; transform-origin:center; animation:atlas-pulse 4s ease-out infinite; }
.atlas-city-ring { fill:none; stroke:#7e9772; stroke-width:1; opacity:.4; }
.atlas-city-core { fill:#fbfaf2; stroke:#62816a; stroke-width:2; }
.atlas-city.selected .atlas-city-core { fill:var(--atlas-orange); stroke:#fff8e9; }
.atlas-city.selected .atlas-city-ring { stroke:var(--atlas-orange); }
.atlas-city.active .atlas-city-ring { opacity:1; stroke-width:1.7; }
.atlas-city text { fill:#5e775d; font-size:12px; paint-order:stroke; stroke:#f6f7ef; stroke-width:3px; stroke-linejoin:round; }
.atlas-city.selected text { fill:#925c43; font-weight:600; }
.atlas-city:hover .atlas-city-core,.atlas-city:focus-visible .atlas-city-core { stroke:var(--atlas-ink); stroke-width:3; }
.atlas-inset > rect { fill:#f6f8ef; stroke:#d9e1cc; stroke-width:.8; }
.atlas-inset path { fill:#dce3d3; stroke:#f8f9f0; stroke-width:.5; }
.atlas-inset path.boundary-mark { fill:#aebda4; stroke:none; }
.atlas-inset text { fill:#99a68b; font-size:8px; }
.atlas-zoom { position:absolute; right:17px; top:18px; display:flex; flex-direction:column; border:1px solid var(--atlas-line); border-radius:7px; overflow:hidden; background:#fffdf7ed; }
.atlas-zoom button { display:grid; place-items:center; width:31px; height:31px; padding:0; border:0; background:none; color:#819672; }
.atlas-zoom button + button { border-top:1px solid var(--atlas-line); }
.atlas-zoom button:hover { background:#eaf0e2; }
.atlas-map-note { position:absolute; left:24px; bottom:21px; display:flex; align-items:center; gap:10px; pointer-events:none; color:#8ca07e; }
.atlas-map-note > svg { box-sizing:content-box; padding:8px; border:1px solid var(--atlas-line); border-radius:50%; }
.atlas-map-note strong,.atlas-map-note small { display:block; font-size:10px; line-height:1.9; font-weight:400; }
.atlas-map-note small { font-size:8px; }
.atlas-legend { display:flex; align-items:center; gap:20px; height:46px; padding:0 22px; border-top:1px solid var(--atlas-line); font-size:9px; color:#8e9a81; }
.atlas-legend span { display:flex; align-items:center; gap:6px; white-space:nowrap; }
.atlas-legend i { display:block; }
.legend-province { width:9px; height:9px; background:#a9b99b; border-radius:2px; }
.legend-city { width:7px; height:7px; border-radius:50%; background:var(--atlas-orange); }
.legend-route { width:16px; border-top:2px dotted var(--atlas-orange); }
.atlas-legend small { margin-left:auto; font-size:8px; }
.atlas-legend span > svg { color:var(--atlas-orange); }
.atlas-status { position:absolute; left:50%; top:45%; transform:translate(-50%,-50%); width:min(310px,80%); padding:22px; border:1px solid var(--atlas-line); border-radius:9px; background:#fffdf5f2; display:flex; flex-direction:column; align-items:center; gap:12px; font-size:12px; color:#718267; box-shadow:0 8px 24px #29402c0d; text-align:center; }
.atlas-status button { border:1px solid var(--atlas-line); border-radius:5px; background:#edf1e4; padding:6px 12px; }
.atlas-empty strong { font:16px var(--serif); }
.atlas-empty span { font-size:11px; line-height:1.9; }
.atlas-home-prompt > span { font-size:11px; line-height:1.9; }
.atlas-home-prompt > strong { font:16px var(--serif); }
.atlas-home-dialog { width:min(460px,calc(100vw - 32px)); max-height:calc(100dvh - 40px); overflow:auto; overscroll-behavior:contain; padding:26px; border:1px solid #d7dfcc; border-radius:14px; color:var(--atlas-ink); background:var(--atlas-panel); box-shadow:0 20px 80px #20382b30; }
.atlas-home-dialog::backdrop { background:#1e352d66; backdrop-filter:blur(3px); }
.atlas-home-dialog form > header { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
.atlas-home-dialog header span { font:8px Georgia,serif; color:#8c997e; letter-spacing:1px !important; }
.atlas-home-dialog h3 { margin:9px 0 0; font:500 24px/1.5 var(--serif); }
.atlas-dialog-close { border:0; background:none; padding:2px; color:#8a987c !important; }
.atlas-home-dialog form > p { margin:13px 0 20px; font-size:11px; line-height:1.9; color:#8c997e; }
.atlas-home-dialog :deep(.city-search) { width:100%; margin-bottom:18px; }
.atlas-home-dialog :deep(.city-search-field) { background:#fffef8; border-color:#d9e1ce; }
.atlas-home-dialog :deep(.city-search-popover) { background:#fffdf5; border-color:#d9e1ce; }
.atlas-home-field { display:grid; gap:7px; font-size:10px; color:#80916f; margin-top:14px; }
.atlas-home-field input { min-width:0; width:100%; padding:10px 11px; color:var(--atlas-ink); border:1px solid #d9e1ce; border-radius:6px; background:#fffef8; font-size:12px; }
.atlas-home-coordinates { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; }
.atlas-home-dialog form > .atlas-home-error { color:#a2553c; margin:10px 0 0; }
.atlas-home-dialog footer { display:flex; align-items:center; justify-content:flex-end; flex-wrap:wrap; gap:10px; margin-top:23px; }
.atlas-home-dialog footer button { padding:9px 12px; border-radius:6px; font-size:11px; }
.atlas-home-remove { margin-right:auto; padding-left:0 !important; border:0; background:none; color:#a56c50 !important; }
.atlas-home-cancel { border:1px solid #d9e1ce; background:none; color:#829271 !important; }
.atlas-home-save { display:flex; align-items:center; gap:6px; border:1px solid var(--atlas-ink); background:var(--atlas-ink); color:#fffaf0 !important; }
.atlas-home-dialog form > small { display:block; font-size:9px; line-height:1.8; color:#a0aa92; margin-top:16px; }
.atlas-journey-panel { display:flex; flex-direction:column; }
.atlas-journey-header { display:flex; justify-content:space-between; align-items:center; padding:19px 21px 17px; }
.atlas-journey-header strong { font-size:14px; font-weight:600; }
.atlas-journey-header > span { font:10px Georgia,serif; color:#9ba68d; }
.atlas-art { height:120px; margin:0 20px; border-radius:7px; overflow:hidden; position:relative; flex-shrink:0; }
.atlas-art svg { width:100%; height:100%; display:block; }
.atlas-art > span { position:absolute; left:14px; top:12px; font-size:7px; color:#6e8463; letter-spacing:1.5px !important; }
.atlas-journey-summary { position:relative; padding:17px 21px 15px; }
.atlas-journey-summary h3 { font:500 22px/1.5 var(--serif); margin:0 0 7px; }
.atlas-month-tag { display:block; font-size:8px; color:#9b7e59; margin-bottom:5px; }
.atlas-journey-summary p { color:#8f9a82; font-size:10px; margin:0 0 14px; line-height:1.8; }
.atlas-journey-summary > div { display:flex; gap:12px; font-size:9px; color:#8c987e; }
.atlas-journey-summary > div > span { display:flex; align-items:center; gap:5px; }
.footprint-list.atlas-timeline { display:flex; flex-direction:column; margin:0 21px; padding:9px 0; border-top:1px solid var(--atlas-line); max-height:230px; overflow:auto; flex:1; gap:0; }
.footprint-list.atlas-timeline button { position:relative; align-items:flex-start; gap:11px; border:0; padding:9px 0 9px 0; width:100%; }
.footprint-list.atlas-timeline button:not(:last-child)::after { content:''; position:absolute; left:4px; top:25px; height:calc(100% - 16px); width:1px; background:#d9dfcc; }
.footprint-list.atlas-timeline .atlas-timeline-dot { width:9px; height:9px; flex-shrink:0; margin-top:5px; border:1px solid #a2ad90; background:var(--atlas-panel); border-radius:50%; z-index:1; }
.footprint-list.atlas-timeline button.active .atlas-timeline-dot { background:var(--atlas-orange); border-color:var(--atlas-orange); box-shadow:0 0 0 3px #efdfd0; }
.atlas-timeline strong { font-size:11px; font-weight:500; }
.footprint-list.atlas-timeline small { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:1; overflow:hidden; font-size:9px; color:#94a087; line-height:1.8; margin-top:5px; }
.atlas-timeline time { flex-shrink:0; margin-top:2px; font:9px Georgia,serif; color:#a0aa92; }
.atlas-memory-detail { margin:10px 20px 0; padding:13px 12px; background:#f1f2e8; border:1px solid #e3e6d8; border-radius:7px; }
.atlas-memory-detail span { font-size:8px; color:#9ba48e; display:block; }
.atlas-memory-detail strong { display:block; font-size:12px; margin:6px 0; font-weight:500; }
.atlas-memory-detail p { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2; overflow:hidden; font-size:10px; line-height:1.8; color:#829173; margin:0; }
.atlas-memory-detail button { display:flex; align-items:center; gap:5px; background:none; border:0; padding:0; margin-top:10px; color:#637b58; font-size:10px; }
.atlas-journey-footer { padding:14px 21px; margin-top:auto; display:flex; align-items:center; justify-content:space-between; color:#9ba58d; font-size:8px; }
.atlas-no-journey { display:flex; align-items:center; gap:10px; margin:18px 21px 30px; color:#8a997c; font-size:11px; line-height:1.9; }
.atlas-journey-strip { display:flex; align-items:center; gap:22px; margin-top:21px; }
.atlas-journey-strip > div:first-child { flex-shrink:0; width:205px; }
.atlas-journey-strip > div:first-child strong { font:15px var(--serif); font-weight:400; }
.atlas-journey-strip > div:first-child small { display:block; font-size:7px; color:#9ba68d; margin-top:8px; letter-spacing:1.1px !important; }
.atlas-journey-cards { display:flex; flex:1; min-width:0; gap:12px; overflow-x:auto; padding-bottom:4px; }
.atlas-journey-cards > button { flex:1 0 220px; max-width:370px; display:flex; align-items:center; gap:10px; padding:13px 14px; text-align:left; background:var(--atlas-panel); border:1px solid var(--atlas-line); border-radius:8px; }
.atlas-journey-cards > button.active { background:#ecf0e3; border-color:#becbb0; }
.atlas-card-icon { width:34px; height:34px; border-radius:50%; border:1px solid #d9dfcc; display:grid; place-items:center; flex-shrink:0; color:#859875; }
.atlas-journey-cards > button.active .atlas-card-icon { color:var(--atlas-orange); }
.atlas-journey-cards strong { display:block; font-size:11px; font-weight:500; }
.atlas-journey-cards small { display:block; color:#939f85; font-size:8px; margin-top:5px; }
.atlas-journey-cards em { margin-left:auto; align-self:flex-start; font:18px Georgia,serif; color:#c2cdb4; }
.is-paused .atlas-route-flow,.is-paused .atlas-city-pulse { animation-play-state:paused; }
@keyframes atlas-flow { to { stroke-dashoffset:-90; } }
@keyframes atlas-pulse { 0% { opacity:.35; transform:scale(.7); } 80%,100% { opacity:0; transform:scale(1.9); } }
:global(.body-grid:has(.footprint-atlas)) { max-width:1920px; grid-template-columns:minmax(0,1fr); gap:0; background:#f6f4ec; }
:global(.body-grid:has(.footprint-atlas) > .right-rail) { display:none; }
:global(.chronicle:has(.footprint-atlas) > .page-head) { display:none; }
:global(.chronicle:has(.footprint-atlas) > .chronicle-stats) { display:none; }
:global(.chronicle:has(.footprint-atlas) > .collection-end) { display:none; }
:global(.chronicle:has(.footprint-atlas) > .line-toolbar) { justify-content:flex-end; padding:0 0 4px; border:0; }
@media(min-width:1600px) { .atlas-workspace { grid-template-columns:minmax(0,1fr) 320px; gap:22px; } .atlas-art { height:145px; } .footprint-list.atlas-timeline { max-height:290px; } }
@media(max-width:1150px) { .atlas-heading h2 { font-size:29px; } .atlas-stats { gap:19px; } .atlas-stats dd { font-size:32px; } .atlas-stats dt { font-size:8px; } .atlas-stats > div + div::before { left:-10px; } .atlas-workspace { grid-template-columns:minmax(0,1fr) 270px; gap:16px; } .atlas-toolbar { padding:0 13px; } .atlas-legend { padding:0 15px; gap:15px; } .atlas-legend small { display:none; } .atlas-journey-strip { display:block; } .atlas-journey-strip > div:first-child { width:auto; margin-bottom:14px; } .atlas-journey-strip > div:first-child small { display:none; } }
@media(max-width:850px) { .atlas-heading { align-items:flex-start; } .atlas-heading h2 { font-size:27px; } .atlas-heading p { font-size:10px; } .atlas-stats { gap:18px; padding-top:20px; } .atlas-stats dd { font-size:28px; } .atlas-workspace { grid-template-columns:minmax(0,1fr); } .atlas-journey-panel { display:grid; grid-template-columns:250px minmax(0,1fr); padding:18px 0; } .atlas-journey-header { grid-column:1/-1; padding-top:0; } .atlas-art { grid-column:1; grid-row:2; } .atlas-journey-summary { grid-column:1; grid-row:3; } .footprint-list.atlas-timeline { grid-column:2; grid-row:2/4; margin-left:10px; } .atlas-memory-detail { grid-column:1/-1; margin-top:12px; } .atlas-journey-footer { grid-column:1/-1; padding-bottom:0; } .atlas-no-journey { grid-column:2; grid-row:2/4; } }
@media(max-width:650px) { .atlas-heading { display:block; padding:14px 0 23px; } .atlas-heading h2 { font-size:29px; } .atlas-stats { justify-content:space-between; padding-top:24px; max-width:350px; } .atlas-stats dd { font-size:33px; } .atlas-stats dt { font-size:9px; } .atlas-stats > div + div::before { left:-21px; } .atlas-eyebrow { font-size:8px; } .atlas-toolbar { height:55px; padding:0 10px; gap:7px; } .atlas-tabs button { padding:7px 9px; font-size:9px; } .atlas-animation-controls { gap:6px; } .atlas-flow-control { gap:5px; font-size:9px; } .footprint-map.atlas-map { height:300px; } .atlas-province-labels { display:none; } .atlas-city text { font-size:24px; stroke-width:4px; } .atlas-city-core { r:7; } .atlas-city-ring { r:12; } .atlas-zoom { top:12px; right:10px; } .atlas-zoom button { width:27px; height:27px; } .atlas-map-note { left:14px; bottom:12px; gap:7px; } .atlas-map-note > svg { width:14px; height:14px; padding:6px; } .atlas-map-note strong { font-size:8px; } .atlas-map-note small { font-size:7px; } .atlas-legend { gap:12px; height:44px; padding:0 14px; font-size:8px; } .atlas-journey-panel { display:flex; padding:0; } .atlas-journey-header { padding-top:19px; } .atlas-art { height:140px; } .atlas-journey-summary h3 { font-size:24px; } .footprint-list.atlas-timeline { margin:0 21px; max-height:250px; } .atlas-timeline strong { font-size:12px; } .atlas-journey-footer { padding-bottom:16px; } .atlas-journey-cards > button { flex-basis:220px; } }
@media(prefers-reduced-motion:reduce) { .atlas-province,.atlas-flow-control i::after { transition:none; } }
@media(max-width:650px) { .atlas-route-options { padding:9px 12px; gap:8px; } .atlas-route-modes > span { display:none; } .atlas-route-modes > button { padding:5px 7px; font-size:9px; } .atlas-home-setting { max-width:125px; font-size:9px; } .atlas-home-marker text { font-size:22px; } .atlas-home-icon { stroke-width:1.6; } .atlas-plane-icon { transform:scale(1.35); } .atlas-home-dialog { padding:20px; } .atlas-home-dialog h3 { font-size:22px; } .atlas-home-dialog footer button { font-size:10px; padding:9px 10px; } }
</style>
