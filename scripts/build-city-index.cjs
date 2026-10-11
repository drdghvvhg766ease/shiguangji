const fs = require('node:fs/promises')
const path = require('node:path')

const directory = path.resolve(__dirname, '../frontend/user/public/maps')
const source = 'https://geo.datav.aliyun.com/areas_v3/bound/'
const standalone = new Set([110000, 120000, 310000, 500000, 710000, 810000, 820000])
// 直辖市/特别行政区已在省级层收录，不再下钻，避免重复
const noDrill = new Set([110000, 120000, 310000, 500000, 810000, 820000])

async function fetchJson(url) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(30000) })
      if (!response.ok) throw new Error(`${url}: ${response.status}`)
      const data = await response.json()
      if (!data.features?.length) throw new Error(`${url}: empty features`)
      return data.features
    } catch (error) {
      if (attempt === 2) throw error
    }
  }
}

function toCity(feature, provinceName) {
  const { properties } = feature
  const [longitude, latitude] = properties.center || properties.centroid || []
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return null
  return {
    code: properties.adcode,
    name: properties.name,
    province: provinceName,
    latitude,
    longitude,
    level: properties.level || 'city',
  }
}

async function loadProvince(province) {
  if (standalone.has(province.adcode)) return []
  const features = await fetchJson(`${source}${province.adcode}_full.json`)
  return features
    .map((feature) => toCity(feature, province.name))
    .filter(Boolean)
}

/** 下钻到县级（示例：阳朔县、平遥县） */
async function loadCounty(city) {
  if (noDrill.has(city.code)) return []
  try {
    const features = await fetchJson(`${source}${city.code}_full.json`)
    return features
      .map((feature) => toCity(feature, city.province))
      .filter(Boolean)
      .map((c) => ({ ...c, level: 'county' }))
  } catch {
    return []
  }
}

async function main() {
  const withCounties = process.argv.includes('--counties')
  const boundary = JSON.parse(
    await fs.readFile(path.join(directory, 'china-provinces.json'), 'utf8'),
  )
  const provinces = boundary.features
    .map((feature) => feature.properties)
    .filter((p) => Number.isInteger(p.adcode))

  // 省级直辖市等作为城市条目
  const cities = provinces
    .filter((p) => standalone.has(p.adcode) && p.adcode !== 710000)
    .map((p) => ({
      code: p.adcode,
      name: p.name,
      province: p.name,
      longitude: p.center[0],
      latitude: p.center[1],
      level: 'city',
    }))

  for (let start = 0; start < provinces.length; start += 4) {
    const results = await Promise.allSettled(
      provinces.slice(start, start + 4).map(loadProvince),
    )
    for (const result of results) {
      if (result.status === 'rejected') throw result.reason
      cities.push(...result.value)
    }
  }

  // DataV 不提供台湾城市中心，沿用既有的台北条目
  cities.push({
    code: 710100,
    name: '台北市',
    province: '台湾省',
    latitude: 25.033,
    longitude: 121.5654,
    level: 'city',
  })

  if (withCounties) {
    const drillable = cities.filter((c) => c.level === 'city' && !noDrill.has(c.code))
    console.log(`下钻 ${drillable.length} 个地级市以收录县级…`)
    const counties = []
    for (let start = 0; start < drillable.length; start += 6) {
      const batch = drillable.slice(start, start + 6)
      const results = await Promise.allSettled(batch.map(loadCounty))
      for (const result of results) {
        if (result.status === 'fulfilled') counties.push(...result.value)
      }
      process.stdout.write(`\r  已收录 ${counties.length} 个县级行政区`)
    }
    process.stdout.write('\n')
    cities.push(...counties)
  }

  // 去重（同一 adcode 只保留一条），再按名称排序
  const seen = new Set()
  const unique = cities.filter((c) => {
    if (seen.has(c.code)) return false
    seen.add(c.code)
    return true
  })
  unique.sort((a, b) => a.code - b.code)

  const minimum = withCounties ? 2000 : 330
  if (unique.length < minimum)
    throw new Error(`Incomplete city index: ${unique.length} < ${minimum}`)

  // 输出缩写字段：索引有数千条，缩写可显著减小体积
  const compact = unique.map((c) => {
    const row = { c: c.code, n: c.name, p: c.province }
    row.l = +c.longitude.toFixed(4)
    row.a = +c.latitude.toFixed(4)
    if (c.level === 'county') row.t = 1
    return row
  })

  await fs.writeFile(
    path.join(directory, 'china-cities.json'),
    JSON.stringify({ source, cities: compact }) + '\n',
  )
  const counties = unique.filter((c) => c.level === 'county').length
  console.log(
    `已生成 ${unique.length} 条地点索引（地级 ${unique.length - counties}，县级 ${counties}）`,
  )
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
