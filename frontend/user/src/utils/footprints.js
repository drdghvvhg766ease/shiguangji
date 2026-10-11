const radians = Math.PI / 180
const firstParallel = 25 * radians
const secondParallel = 47 * radians
const exponent =
  Math.log(Math.cos(firstParallel) / Math.cos(secondParallel)) /
  Math.log(
    Math.tan(Math.PI / 4 + secondParallel / 2) /
      Math.tan(Math.PI / 4 + firstParallel / 2),
  )
const factor =
  (Math.cos(firstParallel) *
    Math.pow(Math.tan(Math.PI / 4 + firstParallel / 2), exponent)) /
  exponent
const originRadius =
  factor / Math.pow(Math.tan(Math.PI / 4 + (36 * radians) / 2), exponent)

function rawProject([longitude, latitude]) {
  const safeLatitude = Math.max(-85, Math.min(85, latitude))
  const radius =
    factor /
    Math.pow(Math.tan(Math.PI / 4 + (safeLatitude * radians) / 2), exponent)
  const theta = exponent * (longitude - 105) * radians
  return [radius * Math.sin(theta), originRadius - radius * Math.cos(theta)]
}

export function locationKey(location) {
  return `${Number(location.latitude).toFixed(3)},${Number(location.longitude).toFixed(3)}`
}

export function normalizeHomeLocation(location) {
  if (
    !location ||
    typeof location.location_name !== 'string' ||
    !location.location_name.trim() ||
    !['number', 'string'].includes(typeof location.latitude) ||
    !['number', 'string'].includes(typeof location.longitude) ||
    String(location.latitude).trim() === '' ||
    String(location.longitude).trim() === '' ||
    !locatedPosts([location]).length
  ) return null
  return {
    location_name: location.location_name.trim().slice(0, 128),
    latitude: Number(location.latitude),
    longitude: Number(location.longitude),
  }
}

export function homeRoutes(home, posts, project) {
  const origin = normalizeHomeLocation(home)
  if (!origin) return []
  const destinations = new Map()
  locatedPosts(posts).forEach((post) => {
    const key = locationKey(post)
    if (key === locationKey(origin)) return
    if (!destinations.has(key)) destinations.set(key, [])
    destinations.get(key).push(post)
  })
  return [...destinations.values()]
    .map((records) => ({
      id: `home-${records.at(-1).id}`,
      path: journeyPath([origin, records.at(-1)], project),
      postIds: records.map((post) => post.id),
    }))
    .filter((route) => route.path)
}

export function locatedPosts(posts) {
  return posts
    .filter(
      (post) =>
        post.latitude != null &&
        post.longitude != null &&
        post.latitude !== '' &&
        post.longitude !== '' &&
        Number.isFinite(Number(post.latitude)) &&
        Number.isFinite(Number(post.longitude)) &&
        Math.abs(Number(post.latitude)) <= 90 &&
        Math.abs(Number(post.longitude)) <= 180,
    )
    .slice()
    .sort(
      (previous, current) =>
        String(previous.event_date || '').localeCompare(
          String(current.event_date || ''),
        ) || Number(previous.id) - Number(current.id),
    )
}

export function groupJourneys(posts) {
  const groups = new Map()
  posts.forEach((post) => {
    const id = post.event_date?.slice(0, 7) || 'undated'
    if (!groups.has(id)) {
      groups.set(id, {
        id,
        name: id === 'undated' ? '未标日期的足迹' : `${id.slice(0, 4)} · ${Number(id.slice(5))}月行记`,
        posts: [],
      })
    }
    groups.get(id).posts.push(post)
  })
  return [...groups.values()].reverse()
}

export function geometryRings(geometry) {
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.flat()
  if (geometry.type === 'Polygon') return geometry.coordinates
  return []
}

function inRing(ring, [longitude, latitude]) {
  let inside = false
  for (
    let currentIndex = 0, previousIndex = ring.length - 1;
    currentIndex < ring.length;
    previousIndex = currentIndex++
  ) {
    const current = ring[currentIndex]
    const previous = ring[previousIndex]
    if (
      current[1] > latitude !== previous[1] > latitude &&
      longitude <
        ((previous[0] - current[0]) * (latitude - current[1])) /
          (previous[1] - current[1]) +
          current[0]
    ) {
      inside = !inside
    }
  }
  return inside
}

export function pointInGeometry(geometry, coordinate) {
  const polygons =
    geometry.type === 'MultiPolygon'
      ? geometry.coordinates
      : geometry.type === 'Polygon'
        ? [geometry.coordinates]
        : []
  return polygons.some(
    (polygon) =>
      polygon.length &&
      inRing(polygon[0], coordinate) &&
      !polygon.slice(1).some((hole) => inRing(hole, coordinate)),
  )
}

export function createChinaProjection(features, posts = []) {
  const coordinates = features
    .filter((feature) => feature.properties.adcode !== '100000_JD')
    .flatMap((feature) => geometryRings(feature.geometry))
    .filter((ring) => ring.every((coordinate) => coordinate[1] >= 17.5))
    .flat()
  coordinates.push(...posts.map((post) => [Number(post.longitude), Number(post.latitude)]))
  if (!coordinates.length) coordinates.push([73, 18], [135, 54])
  const extent = coordinates.reduce(
    (bounds, coordinate) => {
      const point = rawProject(coordinate)
      bounds.left = Math.min(bounds.left, point[0])
      bounds.right = Math.max(bounds.right, point[0])
      bounds.top = Math.max(bounds.top, point[1])
      bounds.bottom = Math.min(bounds.bottom, point[1])
      return bounds
    },
    { left: Infinity, right: -Infinity, top: -Infinity, bottom: Infinity },
  )
  const scale = Math.min(
    910 / Math.max(extent.right - extent.left, 0.01),
    486 / Math.max(extent.top - extent.bottom, 0.01),
  )
  const offsetX = 76 + (910 - (extent.right - extent.left) * scale) / 2
  const offsetY = 42 + (486 - (extent.top - extent.bottom) * scale) / 2
  return (coordinate) => {
    const point = rawProject(coordinate)
    return [
      offsetX + (point[0] - extent.left) * scale,
      offsetY + (extent.top - point[1]) * scale,
    ]
  }
}

export function geometryPath(geometry, project, mainland = false) {
  return geometryRings(geometry)
    .filter((ring) => !mainland || ring.every((coordinate) => coordinate[1] >= 17.5))
    .map(
      (ring) =>
        ring
          .map((coordinate, index) => {
            const point = project(coordinate)
            return `${index ? 'L' : 'M'}${point[0].toFixed(2)},${point[1].toFixed(2)}`
          })
          .join('') + 'Z',
    )
    .join('')
}

export function journeyPath(posts, project) {
  const points = posts.map((post) => project([Number(post.longitude), Number(post.latitude)]))
  if (points.length < 2) return ''
  let route = `M${points[0][0]},${points[0][1]}`
  points.slice(1).forEach((point, index) => {
    const previous = points[index]
    const deltaX = point[0] - previous[0]
    const deltaY = point[1] - previous[1]
    const distance = Math.hypot(deltaX, deltaY)
    if (distance < 0.01) return
    const curve = Math.min(28, distance * 0.22)
    const controlX = (previous[0] + point[0]) / 2 - (deltaY / distance) * curve
    const controlY = (previous[1] + point[1]) / 2 + (deltaX / distance) * curve
    route += ` Q${controlX},${controlY} ${point[0]},${point[1]}`
  })
  return route.includes('Q') ? route : ''
}
