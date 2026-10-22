<template>
  <div ref="host" class="terrain3d" :class="{ 'is-ready': ready }">
    <canvas ref="canvas" class="terrain3d-canvas" aria-label="可旋转的中国足迹立体地图" />
    <div v-if="loading" class="terrain3d-status">
      <span class="terrain3d-spinner" />
      正在堆叠山海…
    </div>
    <div v-else-if="error" class="terrain3d-status terrain3d-error">{{ error }}</div>
    <div
      v-if="tip.show"
      class="terrain3d-tip"
      :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
    >
      <strong>{{ tip.title }}</strong>
      <small>{{ tip.meta }}</small>
    </div>
  </div>
</template>

<script setup>
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import {
  buildProvinceGeometry,
  buildProvinceOutline,
  footprintHeight,
  projectLngLat,
  readThemePalette,
  shiftColor,
} from '../utils/china3d'
import { pointInGeometry } from '../utils/footprints'

const props = defineProps({
  features: { type: Array, default: () => [] },
  posts: { type: Array, default: () => [] },
  selectedIds: { type: [Object, Array], default: () => [] },
  flowing: { type: Boolean, default: true },
  reduced: { type: Boolean, default: false },
})
const emit = defineEmits(['open-post'])

const host = ref(null)
const canvas = ref(null)
const loading = ref(true)
const ready = ref(false)
const error = ref('')
const tip = ref({ show: false, x: 0, y: 0, title: '', meta: '' })

const DEPTH = 0.95
const TOP = DEPTH
const located = computed(() =>
  props.posts.filter((post) => post.latitude != null && post.longitude != null),
)
const cities = computed(() => {
  const grouped = new Map()
  for (const post of located.value) {
    const key = `${Number(post.latitude).toFixed(3)},${Number(post.longitude).toFixed(3)}`
    if (!grouped.has(key)) {
      grouped.set(key, {
        key,
        name: post.location_name || '旅行足迹',
        longitude: Number(post.longitude),
        latitude: Number(post.latitude),
        posts: [],
      })
    }
    const city = grouped.get(key)
    if (post.location_name) city.name = post.location_name
    city.posts.push(post)
  }
  return [...grouped.values()].sort((a, b) => a.key.localeCompare(b.key))
})
const selectedKey = computed(() => {
  const ids = props.selectedIds instanceof Set ? props.selectedIds : new Set(props.selectedIds || [])
  return ids
})

let renderer
let scene
let camera
let controls
let raycaster
let pointer
let provinceGroup
let footprintGroup
let arcGroup
let floor
let hemiLight
let sunLight
let fillLight
let palette = readThemePalette()
let provinceNodes = []
let cityNodes = []
let arcNodes = []
let hoveredProvince = null
let pointerInside = false
let startedAt = 0
let frame = 0
let resizeObserver
let themeObserver
let disposed = false
let active = true
const pointerNdc = new THREE.Vector2()

/** 当前底色是深是浅：深色主题要往亮处提，浅色主题往暗处压 */
function isDarkPaper() {
  const color = new THREE.Color(palette.paper)
  return 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b < 0.3
}

/** 省份立体块的顶面 / 侧面 / 描边配色，明暗主题各一套 */
function plateColors(visited) {
  const dark = isDarkPaper()
  if (visited) {
    return {
      top: dark ? shiftColor(palette.terracotta, 0.1) : shiftColor(palette.terracotta, 0.42),
      side: dark ? shiftColor(palette.terracotta, -0.16) : shiftColor(palette.terracotta, -0.08),
      edge: dark ? shiftColor(palette.terracotta, 0.34) : shiftColor(palette.paper, -0.52),
      edgeOpacity: dark ? 0.55 : 0.8,
    }
  }
  return dark
    ? {
        top: shiftColor(palette.paper, 0.2),
        side: shiftColor(palette.paper, 0.06),
        edge: shiftColor(palette.paper, 0.42),
        edgeOpacity: 0.5,
      }
    : {
        top: shiftColor(palette.paper, -0.1),
        side: shiftColor(palette.paper, -0.3),
        edge: shiftColor(palette.paper, -0.52),
        edgeOpacity: 0.8,
      }
}

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3
}
function clamp01(value) {
  return Math.min(1, Math.max(0, value))
}
function supportsWebgl() {
  try {
    const probe = document.createElement('canvas')
    return Boolean(window.WebGLRenderingContext && (probe.getContext('webgl2') || probe.getContext('webgl')))
  } catch {
    return false
  }
}

/** 柔光沙盘底：用径向渐变贴图撑出落脚感 */
function makeFloorTexture() {
  const size = 256
  const element = document.createElement('canvas')
  element.width = size
  element.height = size
  const context = element.getContext('2d')
  const gradient = context.createRadialGradient(size / 2, size / 2, size * 0.08, size / 2, size / 2, size / 2)
  gradient.addColorStop(0, shiftColor(palette.ink, -0.1).getStyle())
  gradient.addColorStop(0.45, shiftColor(palette.ink, 0.55).getStyle())
  gradient.addColorStop(1, palette.surface)
  context.fillStyle = gradient
  context.fillRect(0, 0, size, size)
  const texture = new THREE.CanvasTexture(element)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

function initScene() {
  renderer = new THREE.WebGLRenderer({
    canvas: canvas.value,
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearAlpha(0)
  scene = new THREE.Scene()

  camera = new THREE.PerspectiveCamera(28, 1, 0.1, 400)
  camera.position.set(0, 42, 38)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, 0.5, 1)
  controls.enableDamping = true
  controls.dampingFactor = 0.075
  controls.enablePan = false
  controls.minDistance = 14
  controls.maxDistance = 62
  controls.minPolarAngle = 0.12
  controls.maxPolarAngle = Math.PI * 0.465
  controls.rotateSpeed = 0.62
  controls.zoomSpeed = 0.72
  controls.update()

  hemiLight = new THREE.HemisphereLight(shiftColor(palette.paper, 0.35), palette.ink, 1.15)
  scene.add(hemiLight)
  sunLight = new THREE.DirectionalLight(0xffedd2, 1.55)
  sunLight.position.set(16, 30, 14)
  scene.add(sunLight)
  fillLight = new THREE.DirectionalLight(0xdfe9ff, 0.42)
  fillLight.position.set(-18, 12, -16)
  scene.add(fillLight)

  floor = new THREE.Mesh(
    new THREE.CircleGeometry(22, 64),
    new THREE.MeshBasicMaterial({ map: makeFloorTexture(), transparent: true, opacity: 0.34, depthWrite: false }),
  )
  floor.rotation.x = -Math.PI / 2
  floor.position.y = -0.04
  scene.add(floor)

  provinceGroup = new THREE.Group()
  footprintGroup = new THREE.Group()
  arcGroup = new THREE.Group()
  scene.add(provinceGroup, footprintGroup, arcGroup)

  raycaster = new THREE.Raycaster()
  pointer = new THREE.Vector2(-10, -10)

  resizeObserver = new ResizeObserver(() => resize())
  resizeObserver.observe(host.value)
  resize()

  renderer.domElement.addEventListener('pointermove', onPointerMove)
  renderer.domElement.addEventListener('pointerleave', onPointerLeave)
  renderer.domElement.addEventListener('click', onClick)
  renderer.domElement.addEventListener('dblclick', resetView)

  themeObserver = new MutationObserver(() => {
    palette = readThemePalette()
    applyPalette()
  })
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme', 'style', 'class'],
  })
}

function resize() {
  if (!renderer || !host.value) return
  const width = host.value.clientWidth
  const height = host.value.clientHeight
  if (!width || !height) return
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
}

function resetView() {
  if (!camera) return
  camera.position.set(0, 42, 38)
  controls.target.set(0, 0.5, 1)
  controls.update()
}

function clearGroup(group) {
  if (!group) return
  while (group.children.length) {
    const child = group.children.pop()
    child.traverse?.((node) => {
      node.geometry?.dispose?.()
      if (Array.isArray(node.material)) node.material.forEach((material) => material.dispose())
      else node.material?.dispose?.()
    })
    group.remove(child)
  }
}

function buildProvinces() {
  clearGroup(provinceGroup)
  provinceNodes = []
  const visited = visitedProvinceCodes()
  props.features.forEach((feature, index) => {
    const geometry = buildProvinceGeometry(feature, { depth: DEPTH })
    if (!geometry) return
    const code = feature.properties?.adcode
    const hit = visited.has(code)
    const plate = plateColors(hit)
    const topColor = plate.top
    const sideColor = plate.side
    const mesh = new THREE.Mesh(geometry, [
      new THREE.MeshStandardMaterial({ color: topColor, roughness: 0.86, metalness: 0.02, flatShading: false }),
      new THREE.MeshStandardMaterial({ color: sideColor, roughness: 0.94, metalness: 0.0 }),
    ])
    mesh.position.y = -3
    mesh.userData = { code, name: feature.properties?.name || '', feature, index }
    provinceGroup.add(mesh)

    const outline = buildProvinceOutline(feature, { height: DEPTH + 0.04 })
    if (outline) {
      const line = new THREE.LineSegments(
        outline,
        new THREE.LineBasicMaterial({ color: plate.edge, transparent: true, opacity: plate.edgeOpacity }),
      )
      line.position.y = -3
      line.userData = { follows: mesh, offset: 0 }
      mesh.userData.outline = line
      provinceGroup.add(line)
    }
    provinceNodes.push({ mesh, feature, index, targetLift: 0 })
  })
}

function visitedProvinceCodes() {
  const codes = new Set()
  const points = located.value.map((post) => [Number(post.longitude), Number(post.latitude)])
  if (!points.length) return codes
  for (const feature of props.features) {
    const geometry = feature.geometry
    if (!geometry) continue
    if (points.some((point) => pointInGeometry(geometry, point))) codes.add(feature.properties?.adcode)
  }
  return codes
}

function buildFootprints() {
  clearGroup(footprintGroup)
  cityNodes = []
  const pinMaterial = new THREE.MeshStandardMaterial({
    color: palette.terracotta,
    roughness: 0.55,
    metalness: 0.08,
    emissive: shiftColor(palette.terracotta, -0.45),
    emissiveIntensity: 0.45,
  })
  const headMaterial = new THREE.MeshStandardMaterial({
    color: shiftColor(palette.gold, 0.18),
    roughness: 0.34,
    metalness: 0.2,
    emissive: shiftColor(palette.gold, -0.4),
    emissiveIntensity: 0.5,
  })
  const ringMaterial = new THREE.MeshBasicMaterial({
    color: palette.terracotta,
    transparent: true,
    opacity: 0.42,
    side: THREE.DoubleSide,
  })
  const stemGeometry = new THREE.CylinderGeometry(0.12, 0.2, 1, 8, 1)
  const headGeometry = new THREE.SphereGeometry(0.33, 16, 12)
  const ringGeometry = new THREE.RingGeometry(0.4, 0.56, 26)

  cities.value.forEach((city, index) => {
    const [x, z] = projectLngLat([city.longitude, city.latitude])
    const height = footprintHeight(city.posts.length)
    const stem = new THREE.Mesh(stemGeometry, pinMaterial)
    stem.position.set(x, TOP + height / 2, z)
    stem.scale.y = 0.001
    stem.userData = { city, kind: 'city' }
    footprintGroup.add(stem)

    const head = new THREE.Mesh(headGeometry, headMaterial)
    head.position.set(x, TOP, z)
    head.userData = { city, kind: 'city' }
    footprintGroup.add(head)

    const ring = new THREE.Mesh(ringGeometry, ringMaterial.clone())
    ring.rotation.x = -Math.PI / 2
    ring.position.set(x, TOP + 0.03, z)
    footprintGroup.add(ring)

    cityNodes.push({ city, stem, head, ring, height, index, base: performance.now() })
  })
  applySelection()
}

function buildArcs() {
  clearGroup(arcGroup)
  arcNodes = []
  const ordered = located.value
    .slice()
    .sort((a, b) => String(a.event_date).localeCompare(String(b.event_date)) || a.id - b.id)
  const points = []
  for (const post of ordered) {
    const key = `${Number(post.latitude).toFixed(3)},${Number(post.longitude).toFixed(3)}`
    if (!points.length || points[points.length - 1].key !== key) {
      const [x, z] = projectLngLat([Number(post.longitude), Number(post.latitude)])
      points.push({ key, x, z })
    }
  }
  if (points.length < 2) return
  const curveMaterial = new THREE.MeshBasicMaterial({
    color: palette.pine,
    transparent: true,
    opacity: 0.62,
  })
  const sparkMaterial = new THREE.MeshBasicMaterial({ color: palette.gold })
  const sparkGeometry = new THREE.SphereGeometry(0.19, 10, 8)
  for (let i = 1; i < points.length; i += 1) {
    const from = points[i - 1]
    const to = points[i]
    const distance = Math.hypot(to.x - from.x, to.z - from.z)
    if (distance < 0.4) continue
    const start = new THREE.Vector3(from.x, TOP + 0.1, from.z)
    const end = new THREE.Vector3(to.x, TOP + 0.1, to.z)
    const mid = new THREE.Vector3(
      (from.x + to.x) / 2,
      TOP + 1.4 + Math.min(distance * 0.34, 6.5),
      (from.z + to.z) / 2,
    )
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end)
    const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 44, 0.055, 6, false), curveMaterial)
    arcGroup.add(tube)
    const spark = new THREE.Mesh(sparkGeometry, sparkMaterial)
    arcGroup.add(spark)
    arcNodes.push({ curve, spark, offset: (i * 0.17) % 1 })
  }
}

function applySelection() {
  const ids = selectedKey.value
  for (const node of cityNodes) {
    const hit = node.city.posts.some((post) => ids.has(post.id))
    const scale = hit ? 1.45 : 1
    node.head.scale.setScalar(scale)
    node.ring.material.opacity = hit ? 0.78 : 0.4
    node.ring.scale.setScalar(hit ? 1.35 : 1)
  }
}

function applyPalette() {
  if (!scene) return
  hemiLight.groundColor = new THREE.Color(palette.ink)
  hemiLight.color.set(shiftColor(palette.paper, isDarkPaper() ? 0.28 : 0.35))
  floor.material.map?.dispose()
  floor.material.map = makeFloorTexture()
  floor.material.needsUpdate = true
  const visited = visitedProvinceCodes()
  for (const node of provinceNodes) {
    const hit = visited.has(node.mesh.userData.code)
    const plate = plateColors(hit)
    const [top, side] = node.mesh.material
    top.color.set(plate.top)
    side.color.set(plate.side)
    const outline = node.mesh.userData.outline
    if (outline) {
      outline.material.color.set(plate.edge)
      outline.material.opacity = plate.edgeOpacity
    }
  }
  for (const node of cityNodes) {
    node.stem.material.color.set(palette.terracotta)
    node.stem.material.emissive.set(shiftColor(palette.terracotta, -0.45))
    node.head.material.color.set(shiftColor(palette.gold, 0.18))
    node.head.material.emissive.set(shiftColor(palette.gold, -0.4))
    node.ring.material.color.set(palette.terracotta)
  }
  for (const node of arcNodes) {
    node.spark.material.color.set(palette.gold)
  }
  arcGroup.children.forEach((child) => {
    if (child.isMesh && child.geometry.type === 'TubeGeometry') child.material.color.set(palette.pine)
  })
}

function onPointerMove(event) {
  if (!renderer) return
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  pointerNdc.set(event.clientX - rect.left, event.clientY - rect.top)
  pointerInside = true
}

function onPointerLeave() {
  pointer.set(-10, -10)
  pointerInside = false
  hoveredProvince = null
  tip.value.show = false
}

function pick() {
  if (!renderer) return null
  raycaster.setFromCamera(pointer, camera)
  const cityHits = raycaster.intersectObjects(cityNodes.map((node) => node.head), false)
  if (cityHits.length) return { type: 'city', city: cityHits[0].object.userData.city }
  const provinceHits = raycaster.intersectObjects(provinceNodes.map((node) => node.mesh), false)
  if (provinceHits.length) {
    const mesh = provinceHits[0].object
    return { type: 'province', mesh, name: mesh.userData.name, code: mesh.userData.code }
  }
  return null
}

function provincePostCount(code) {
  const feature = props.features.find((item) => item.properties?.adcode === code)
  if (!feature) return 0
  return located.value.filter((post) => pointInGeometry(feature.geometry, [Number(post.longitude), Number(post.latitude)])).length
}

function onClick() {
  const hit = pick()
  if (!hit || hit.type !== 'city') return
  const posts = hit.city.posts
  const ids = selectedKey.value
  const target = posts.filter((post) => ids.has(post.id)).at(-1) || posts.at(-1)
  if (target) emit('open-post', { id: target.id })
}

function updateHover() {
  if (!pointerInside) {
    hoveredProvince = null
    tip.value.show = false
    return
  }
  const hit = pick()
  if (!hit) {
    hoveredProvince = null
    tip.value.show = false
    return
  }
  if (hit.type === 'city') {
    hoveredProvince = null
    tip.value = {
      show: true,
      x: pointerNdc.x + 14,
      y: pointerNdc.y - 10,
      title: hit.city.name,
      meta: `${hit.city.posts.length} 条记录 · 点击回看`,
    }
    renderer.domElement.style.cursor = 'pointer'
    return
  }
  hoveredProvince = hit.mesh
  const count = provincePostCount(hit.code)
  tip.value = {
    show: Boolean(hit.name),
    x: pointerNdc.x + 14,
    y: pointerNdc.y - 10,
    title: hit.name || '',
    meta: count ? `${count} 条足迹落在这里` : '还没有留下足迹',
  }
  renderer.domElement.style.cursor = 'grab'
}

function tick() {
  if (disposed) return
  frame = requestAnimationFrame(tick)
  if (!active) return
  const elapsed = (performance.now() - startedAt) / 1000
  controls.update()

  for (const node of provinceNodes) {
    const progress = clamp01((elapsed - node.index * 0.014) / 0.6)
    const drop = -3 * (1 - easeOutCubic(progress))
    const lift = node.mesh === hoveredProvince ? 0.34 : 0
    node.mesh.position.y = drop + lift
    const outline = node.mesh.userData.outline
    if (outline) outline.position.y = node.mesh.position.y
  }

  for (const node of cityNodes) {
    const progress = clamp01((elapsed - 0.42 - node.index * 0.022) / 0.62)
    const grown = easeOutCubic(progress) * node.height
    node.stem.scale.y = Math.max(0.001, grown / node.height)
    node.stem.position.y = TOP + grown / 2
    node.head.position.y = TOP + grown
    node.ring.position.y = TOP + 0.03
    if (props.flowing && !props.reduced) {
      const pulse = 1 + Math.sin(elapsed * 2.4 + node.index) * 0.12
      node.ring.scale.setScalar(pulse * (node.head.scale.x > 1.1 ? 1.35 : 1))
    }
  }

  if (props.flowing && !props.reduced) {
    for (const node of arcNodes) {
      const t = (elapsed * 0.22 + node.offset) % 1
      node.curve.getPoint(t, node.spark.position)
    }
  }

  updateHover()
  renderer.render(scene, camera)
}

function rebuild() {
  if (!scene) return
  buildProvinces()
  buildFootprints()
  buildArcs()
  startedAt = performance.now()
  loading.value = false
  ready.value = true
}

onMounted(() => {
  if (!supportsWebgl()) {
    loading.value = false
    error.value = '当前浏览器未开启 WebGL，先看看平面地图吧。'
    return
  }
  initScene()
  loading.value = true
  // 等首帧画布尺寸落定再建模型，避免 0 宽高导致相机比例异常
  requestAnimationFrame(() => {
    if (disposed) return
    rebuild()
    tick()
  })
})

watch(() => props.features, () => {
  if (scene && props.features.length) rebuild()
})
watch(() => props.posts, () => {
  if (!scene) return
  buildFootprints()
  buildArcs()
  applyPalette()
}, { deep: false })
watch(selectedKey, applySelection)
watch(() => props.flowing, () => {
  if (!props.flowing) arcNodes.forEach((node) => node.spark.position.set(0, -999, 0))
})

onActivated(() => {
  active = true
  resize()
  if (!frame && scene) tick()
})
onDeactivated(() => {
  active = false
})
onBeforeUnmount(() => {
  disposed = true
  active = false
  cancelAnimationFrame(frame)
  frame = 0
  resizeObserver?.disconnect()
  themeObserver?.disconnect()
  renderer?.domElement.removeEventListener('pointermove', onPointerMove)
  renderer?.domElement.removeEventListener('pointerleave', onPointerLeave)
  renderer?.domElement.removeEventListener('click', onClick)
  renderer?.domElement.removeEventListener('dblclick', resetView)
  controls?.dispose()
  scene?.traverse((node) => {
    node.geometry?.dispose?.()
    if (Array.isArray(node.material)) node.material.forEach((material) => material.dispose?.())
    else node.material?.dispose?.()
    node.material?.map?.dispose?.()
  })
  renderer?.dispose()
  scene = null
})
</script>

<style scoped>
.terrain3d {
  position: relative;
  width: 100%;
  height: clamp(460px, 54vh, 660px);
  border-radius: 12px;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 34%, color-mix(in srgb, var(--surface, #fbfaf5) 92%, var(--terracotta, #ad4737) 8%) 0%, var(--paper, #f6f4ec) 62%),
    var(--paper, #f6f4ec);
  isolation: isolate;
}
.terrain3d::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle at 1px 1px, color-mix(in srgb, var(--ink, #26483e) 12%, transparent) 1px, transparent 0);
  background-size: 26px 26px;
  opacity: 0.35;
  pointer-events: none;
}
.terrain3d-canvas {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: grab;
  opacity: 0;
  transition: opacity 0.6s ease;
}
.is-ready .terrain3d-canvas {
  opacity: 1;
}
.terrain3d-canvas:active {
  cursor: grabbing;
}
.terrain3d-status {
  position: absolute;
  left: 50%;
  top: 46%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  border-radius: 9px;
  border: 1px solid var(--line, #dfe4d5);
  background: color-mix(in srgb, var(--surface, #fbfaf5) 92%, transparent);
  font-size: 12px;
  color: var(--muted, #819078);
  backdrop-filter: blur(4px);
}
.terrain3d-error {
  max-width: 260px;
  text-align: center;
  line-height: 1.8;
  color: var(--terracotta, #ad4737);
}
.terrain3d-spinner {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 2px solid color-mix(in srgb, var(--terracotta, #ad4737) 30%, transparent);
  border-top-color: var(--terracotta, #ad4737);
  animation: terrain-spin 0.8s linear infinite;
}
@keyframes terrain-spin {
  to {
    transform: rotate(360deg);
  }
}
.terrain3d-tip {
  position: absolute;
  z-index: 3;
  padding: 7px 11px;
  border-radius: 7px;
  border: 1px solid color-mix(in srgb, var(--line, #dfe4d5) 70%, transparent);
  background: color-mix(in srgb, var(--surface, #fbfaf5) 94%, transparent);
  box-shadow: 0 6px 20px color-mix(in srgb, var(--ink, #26483e) 14%, transparent);
  pointer-events: none;
  display: grid;
  gap: 3px;
  transform: translate3d(0, 0, 0);
  white-space: nowrap;
}
.terrain3d-tip strong {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink, #26483e);
}
.terrain3d-tip small {
  font-size: 10px;
  color: var(--muted, #819078);
}
.terrain3d-foot {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 14px;
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 10px;
  color: var(--muted, #819078);
  pointer-events: none;
}
.terrain3d-legend {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.terrain3d-legend i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: block;
}
.terrain3d-legend .pin {
  background: var(--terracotta, #ad4737);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--terracotta, #ad4737) 22%, transparent);
}
.terrain3d-legend .land {
  width: 11px;
  height: 8px;
  border-radius: 2px;
  background: color-mix(in srgb, var(--terracotta, #ad4737) 55%, var(--line, #dfe4d5));
}
.terrain3d-tips {
  margin-left: auto;
  letter-spacing: 0.4px;
}
@media (max-width: 650px) {
  .terrain3d {
    height: 340px;
  }
  .terrain3d-tips {
    display: none;
  }
  .terrain3d-foot {
    bottom: 10px;
    left: 12px;
    gap: 12px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .terrain3d-canvas {
    transition: none;
  }
  .terrain3d-spinner {
    animation: none;
  }
}
</style>
