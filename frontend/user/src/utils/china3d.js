/**
 * 中国地图三维几何构建。
 *
 * 数据源为本地 public/maps/china-provinces.json（DataV 标准省级边界），
 * 运行时不请求任何在线瓦片、不依赖地图密钥。这里只做「几何 → BufferGeometry」的转换，
 * 让足迹地图从平面插画变成可以转动的立体沙盘。
 */
import * as THREE from 'three'

/** 经纬度 → 平面坐标：经度差乘余弦收缩，避免高纬被拉长 */
const ORIGIN = [104, 36]
const LON_SCALE = 0.62
const LAT_SCALE = 0.68
/**
 * 环的最小跨度（度）。低于此值的碎环挤出来只有亚像素宽，
 * 但阈值不能设太大——澳门特别行政区整体跨度只有 0.1 度左右，
 * 过滤掉就会在国家版图上缺失一块。
 */
const MIN_RING_SPAN = 0.045

export function projectLngLat([longitude, latitude]) {
  return [(longitude - ORIGIN[0]) * LON_SCALE, -(latitude - ORIGIN[1]) * LAT_SCALE]
}

/** 环的包围盒面积，用来过滤退化的碎环 */
function ringSpan(ring) {  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  for (const point of ring) {
    if (point[0] < minX) minX = point[0]
    if (point[0] > maxX) maxX = point[0]
    if (point[1] < minY) minY = point[1]
    if (point[1] > maxY) maxY = point[1]
  }
  return Math.max(maxX - minX, maxY - minY)
}

/** 整个要素的包围盒跨度（度），用来给小行政区放宽容差与过滤阈值 */
function geometrySpan(geometry) {
  const polygons = geometry.type === 'MultiPolygon' ? geometry.coordinates : [geometry.coordinates]
  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  for (const polygon of polygons) {
    for (const ring of polygon) {
      for (const point of ring) {
        if (point[0] < minX) minX = point[0]
        if (point[0] > maxX) maxX = point[0]
        if (point[1] < minY) minY = point[1]
        if (point[1] > maxY) maxY = point[1]
      }
    }
  }
  return Math.max(maxX - minX, maxY - minY) || 0
}

/**
 * 按要素规模给出简化容差与最小环跨度。
 * 0.06 度的固定容差等于 6 公里，会把澳门整个轮廓压成一条线，
 * 所以小行政区要用更细的容差；反过来大省用细容差会多出几万个面。
 */
function resolutionFor(geometry) {
  const span = geometrySpan(geometry)
  return {
    tolerance: Math.min(0.06, Math.max(0.0012, span * 0.015)),
    minRing: span < 2 ? 0.002 : MIN_RING_SPAN,
  }
}

/** Douglas-Peucker：把两万多个点降到几千，挤出面数可控 */
function simplify(ring, tolerance) {
  if (ring.length < 4) return ring
  const keep = new Uint8Array(ring.length)
  keep[0] = 1
  keep[ring.length - 1] = 1
  const stack = [[0, ring.length - 1]]
  while (stack.length) {
    const [from, to] = stack.pop()
    let maxDist = -1
    let index = -1
    const [x1, y1] = ring[from]
    const [x2, y2] = ring[to]
    const dx = x2 - x1
    const dy = y2 - y1
    const length = Math.hypot(dx, dy)
    for (let i = from + 1; i < to; i += 1) {
      const [x, y] = ring[i]
      const distance = length === 0
        ? Math.hypot(x - x1, y - y1)
        : Math.abs(dy * x - dx * y + x2 * y1 - y2 * x1) / length
      if (distance > maxDist) {
        maxDist = distance
        index = i
      }
    }
    if (maxDist > tolerance && index > 0) {
      keep[index] = 1
      stack.push([from, index], [index, to])
    }
  }
  return ring.filter((_, i) => keep[i])
}

function ringToPoints(ring, tolerance) {
  const closed = ring.length > 1
    && ring[0][0] === ring[ring.length - 1][0]
    && ring[0][1] === ring[ring.length - 1][1]
  const source = closed ? ring.slice(0, -1) : ring
  const simplified = simplify(source, tolerance)
  return simplified.map((point) => projectLngLat(point))
}

/**
 * 单个省级要素 → 挤出几何体。
 * 每个多边形取外环做一个 Shape，其余环视为岛屿独立挤出（中国省级边界基本无内洞）。
 */
export function buildProvinceGeometry(feature, { depth = 1.15, tolerance } = {}) {
  const geometry = feature.geometry
  const scale = resolutionFor(geometry)
  const epsilon = tolerance ?? scale.tolerance
  const minRing = scale.minRing
  const polygons = geometry.type === 'MultiPolygon' ? geometry.coordinates : [geometry.coordinates]
  const shapes = []
  for (const polygon of polygons) {
    for (const ring of polygon) {
      if (!Array.isArray(ring) || ring.length < 4) continue
      if (ringSpan(ring) < minRing) continue // 极小的礁石环，挤出后不可见
      const points = ringToPoints(ring, epsilon)
      if (points.length < 3) continue
      // 挤出后 rotateX(-90°) 会把 shape 的 y 映射成 -z，这里先取负抵消，
      // 保证北方在屏幕深处、南方在近处。
      const shape = new THREE.Shape()
      shape.moveTo(points[0][0], -points[0][1])
      for (let i = 1; i < points.length; i += 1) shape.lineTo(points[i][0], -points[i][1])
      shape.closePath()
      shapes.push(shape)
    }
  }
  if (!shapes.length) return null
  const merged = new THREE.ExtrudeGeometry(shapes, {
    depth,
    bevelEnabled: false,
    curveSegments: 1,
    steps: 1,
  })
  merged.rotateX(-Math.PI / 2) // 挤出方向转为向上，纬度增大朝屏幕里
  merged.computeVertexNormals()
  return merged
}

/** 省份轮廓线（用于顶面描边，让立体块之间有清晰的拼缝） */
export function buildProvinceOutline(feature, { tolerance, height = 0 } = {}) {
  const geometry = feature.geometry
  const scale = resolutionFor(geometry)
  const epsilon = tolerance ?? scale.tolerance
  // 描边只跟大轮廓走：几百个小礁石环各自描边会糊成一片划痕，
  // 面照样挤出，只是不画线。
  const minRing = Math.max(scale.minRing, 0.1)
  const polygons = geometry.type === 'MultiPolygon' ? geometry.coordinates : [geometry.coordinates]
  const positions = []
  for (const polygon of polygons) {
    for (const ring of polygon) {
      if (!Array.isArray(ring) || ring.length < 4) continue
      if (ringSpan(ring) < minRing) continue
      const points = ringToPoints(ring, epsilon)
      if (points.length < 3) continue
      for (let i = 0; i < points.length; i += 1) {
        const current = points[i]
        const next = points[(i + 1) % points.length]
        positions.push(current[0], height, -current[1], next[0], height, -next[1])
      }
    }
  }
  if (!positions.length) return null
  const buffer = new THREE.BufferGeometry()
  buffer.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  return buffer
}

/** 从 CSS 变量取当前主题色，主题切换时整体重新上色 */
export function readThemePalette(element) {
  const host = element || document.documentElement
  const styles = getComputedStyle(host)
  const read = (name, fallback) => {
    const value = styles.getPropertyValue(name).trim()
    return value || fallback
  }
  return {
    paper: read('--paper', '#f6f4ec'),
    surface: read('--surface', '#fbfaf5'),
    ink: read('--ink', '#26483e'),
    muted: read('--muted', '#819078'),
    line: read('--line', '#dfe4d5'),
    terracotta: read('--terracotta', '#ad4737'),
    pine: read('--pine', '#3c6255'),
    gold: read('--gold', '#c9a227'),
  }
}

/** 把 #rrggbb / rgb() 颜色按比例加深或提亮 */
export function shiftColor(color, amount) {
  const parsed = new THREE.Color(color)
  const target = amount < 0 ? new THREE.Color(0x000000) : new THREE.Color(0xffffff)
  return parsed.lerp(target, Math.abs(amount))
}

/** 某点的省份顶面高度之上的柱高：记录越多，脚印立柱越高 */
export function footprintHeight(count) {
  return 0.9 + Math.min(count, 8) * 0.42
}
