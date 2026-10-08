const fs = require('node:fs/promises')
const path = require('node:path')

const directory = path.resolve(__dirname, '../frontend/user/public/maps')
const source = 'https://geo.datav.aliyun.com/areas_v3/bound/'
const standalone = new Set([110000, 120000, 310000, 500000, 710000, 810000, 820000])

async function loadProvince(province) {
  if (standalone.has(province.adcode)) return []
  const url = `${source}${province.adcode}_full.json`
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(30000) })
      if (!response.ok) throw new Error(`${url}: ${response.status}`)
      const data = await response.json()
      if (!data.features?.length) throw new Error(`${url}: empty features`)
      return data.features.map(({ properties: city }) => {
        const [longitude, latitude] = city.center || city.centroid || []
        if (!Number.isFinite(longitude) || !Number.isFinite(latitude))
          throw new Error(`${city.name}: missing coordinates`)
        return { code: city.adcode, name: city.name, province: province.name, latitude, longitude }
      })
    } catch (error) {
      if (attempt === 2) throw error
    }
  }
}

async function main() {
  const boundary = JSON.parse(await fs.readFile(path.join(directory, 'china-provinces.json'), 'utf8'))
  const provinces = boundary.features.map(feature => feature.properties).filter(p => Number.isInteger(p.adcode))
  const cities = provinces.filter(p => standalone.has(p.adcode) && p.adcode !== 710000).map(p => ({
    code: p.adcode, name: p.name, province: p.name,
    longitude: p.center[0], latitude: p.center[1],
  }))
  for (let start = 0; start < provinces.length; start += 4) {
    const results = await Promise.allSettled(provinces.slice(start, start + 4).map(loadProvince))
    for (const result of results) {
      if (result.status === 'rejected') throw result.reason
      cities.push(...result.value)
    }
  }
  // DataV does not provide Taiwan city centers; retain the existing Taipei choice.
  cities.push({ code: 710100, name: '台北市', province: '台湾省', latitude: 25.033, longitude: 121.5654 })
  cities.sort((a, b) => a.code - b.code)
  if (cities.length < 330) throw new Error(`Incomplete city index: ${cities.length}`)
  await fs.writeFile(path.join(directory, 'china-cities.json'), JSON.stringify({ source, cities }) + '\n')
  console.log(`Generated ${cities.length} local city/region centers`)
}

main().catch(error => { console.error(error); process.exitCode = 1 })
