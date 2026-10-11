const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')

const base = process.env.WEB_BASE || 'http://127.0.0.1:5173'
const posts = [
  ['西安', 108.9398, 34.3416, '2026-07-12'],
  ['成都', 104.0665, 30.5728, '2026-07-14'],
  ['大理', 100.2676, 25.6065, '2026-07-17'],
  ['拉萨', 91.1322, 29.6604, '2026-07-21'],
  ['北京', 116.4074, 39.9042, '2026-09-02'],
  ['南京', 118.7969, 32.0603, '2026-09-05'],
  ['上海', 121.4737, 31.2304, '2026-09-07'],
  ['杭州', 120.1551, 30.2741, '2026-09-10'],
  ['广州', 113.2644, 23.1291, '2026-05-01'],
  ['桂林', 110.2991, 25.2742, '2026-05-03'],
  ['厦门', 118.0894, 24.4798, '2026-05-05'],
  ['海口', 110.1983, 20.044, '2026-05-08'],
].map(([location_name, longitude, latitude, event_date], index) => ({
  id: index + 1, location_name, longitude, latitude, event_date,
  nickname: '旅途收藏家', content: `${location_name}的风景，留在这一天的记忆里。`,
}))

async function aircraftTransform(page) {
  return page.locator('.atlas-plane').first().evaluate(element => {
    const matrix = element.getCTM()
    return JSON.stringify([matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f])
  })
}

async function mount(page, data = posts) {
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, json: { detail: 'isolated component check' } }))
  await page.goto(base)
  await page.locator('.login-form').waitFor()
  await page.evaluate(async data => {
    const { createApp, h, ref } = await import('/node_modules/.vite/deps/vue.js')
    const { default: FootprintMap } = await import('/src/components/FootprintMap.vue')
    const root = document.getElementById('app')
    root.__vue_app__.unmount()
    const records = ref(data)
    const picking = ref(false)
    const location = ref(null)
    const userId = ref(101)
    const opens = []
    window.atlasHarness = { records, picking, location, userId, opens }
    createApp({
      setup() {
        return () => h('main', { style: 'height:100dvh;overflow:auto;padding:24px;background:#f6f4ec' }, [
          h(FootprintMap, {
            key: picking.value ? 'picker' : 'atlas',
            posts: records.value, picking: picking.value, modelValue: location.value,
            userId: userId.value,
            'onUpdate:modelValue': value => { location.value = value },
            onOpenPost: value => opens.push(value),
          }),
        ])
      },
    }).mount(root)
  }, data)
  await page.waitForFunction(() => document.querySelectorAll('.atlas-province').length === 35)
}

async function main() {
  const utilities = await import(pathToFileURL(path.resolve(__dirname, '../frontend/user/src/utils/footprints.js')))
  const geography = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../frontend/user/public/maps/china-provinces.json')))
  for (const [name, coordinate] of [
    ['四川省', [104.0665, 30.5728]], ['海南省', [110.1983, 20.044]],
    ['台湾省', [121.5654, 25.033]], ['香港特别行政区', [114.1694, 22.3193]],
    ['澳门特别行政区', [113.5439, 22.1987]],
  ]) {
    assert(utilities.pointInGeometry(geography.features.find(feature => feature.properties.name === name).geometry, coordinate), name)
  }
  const islandAndHole = { type: 'MultiPolygon', coordinates: [
    [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]],
    [[[20, 20], [25, 20], [25, 25], [20, 25], [20, 20]]],
  ] }
  assert.equal(utilities.pointInGeometry(islandAndHole, [3, 3]), false)
  assert.equal(utilities.pointInGeometry(islandAndHole, [22, 22]), true)
  assert.equal(utilities.pointInGeometry(islandAndHole, [15, 15]), false)
  const invalid = [null, '', 'invalid', 91].map(latitude => ({ id: 90, latitude, longitude: 120 }))
  assert.equal(utilities.locatedPosts([...posts, ...invalid]).length, 12)
  const projected = utilities.createChinaProjection(geography.features, posts)
  const repeated = [posts[0], { ...posts[0], id: 99 }]
  assert.equal(utilities.journeyPath(repeated, projected), '')
  assert(!utilities.journeyPath([posts[0], posts[1]], projected).includes('NaN'))
  assert.equal(utilities.groupJourneys(utilities.locatedPosts(posts))[0].id, '2026-09')
  const origin = { location_name: '广州 · 我的家', latitude: 23.1291, longitude: 113.2644 }
  assert.equal(utilities.normalizeHomeLocation(null), null)
  for (const badLocation of [
    { ...origin, latitude: '' }, { ...origin, longitude: ' ' },
    { ...origin, latitude: 91 }, { ...origin, longitude: true },
    { ...origin, location_name: '' }, { ...origin, latitude: 'wrong' },
  ]) assert.equal(utilities.normalizeHomeLocation(badLocation), null)
  assert.deepEqual(utilities.normalizeHomeLocation({ ...origin, latitude: '23.1291' }), origin)
  assert.equal(utilities.homeRoutes(null, posts, projected).length, 0)
  const branches = utilities.homeRoutes(origin, [...posts, { ...posts[0], id: 99 }], projected)
  assert.equal(branches.length, 11)
  assert.equal(branches.find(route => route.postIds.includes(1)).postIds.length, 2)
  const originPoint = projected([origin.longitude, origin.latitude])
  assert(branches.every(route => route.path.startsWith(`M${originPoint[0]},${originPoint[1]} Q`)))

  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'warning' && message.text().includes('[Vue warn]')) errors.push(message.text()) })
  try {
    await mount(page)
    assert.equal(await page.locator('.atlas-city').count(), 12)
    assert.equal(await page.locator('.atlas-province.visited').count(), 12)
    assert.equal(await page.locator('.atlas-route').count(), 3)
    assert.equal(await page.locator('.atlas-plane').count(), 3)
    assert.equal(await page.locator('animateMotion').first().getAttribute('rotate'), 'auto')
    const planeTransform = await aircraftTransform(page)
    assert.equal(await page.locator('.atlas-journey-cards button').count(), 3)
    const before = await page.locator('.atlas-route-flow').first().evaluate(element => getComputedStyle(element).strokeDashoffset)
    await page.waitForTimeout(160)
    assert.notEqual(await aircraftTransform(page), planeTransform)
    assert.notEqual(await page.locator('.atlas-route-flow').first().evaluate(element => getComputedStyle(element).strokeDashoffset), before)
    await page.getByRole('switch', { name: '轨迹流动动画' }).click()
    const stopped = await page.locator('.atlas-route-flow').first().evaluate(element => getComputedStyle(element).strokeDashoffset)
    const stoppedTime = await page.locator('.atlas-svg').evaluate(element => element.getCurrentTime())
    const stoppedPlane = await aircraftTransform(page)
    await page.waitForTimeout(160)
    assert.equal(await page.locator('.atlas-route-flow').first().evaluate(element => getComputedStyle(element).strokeDashoffset), stopped)
    assert.equal(await aircraftTransform(page), stoppedPlane)
    assert(Math.abs(await page.locator('.atlas-svg').evaluate(element => element.getCurrentTime()) - stoppedTime) < .01)
    await page.getByRole('switch', { name: '轨迹流动动画' }).click()
    await page.locator('.atlas-speed').click()
    assert.equal(await page.locator('animateMotion').first().getAttribute('dur'), '3.5s')
    await page.getByRole('button', { name: '本月旅程', exact: true }).click()
    assert.equal(await page.locator('.atlas-city').count(), 4)
    assert.equal(await page.locator('.atlas-route').count(), 1)
    await page.locator('.atlas-journey-cards button').filter({ hasText: '7月行记' }).click()
    await page.getByRole('button', { name: '查看成都的足迹，1条记录', exact: true }).click()
    assert.equal(await page.locator('.atlas-memory-detail strong').textContent(), '成都')
    await page.getByRole('button', { name: '打开这段回忆', exact: true }).click()
    assert.deepEqual(await page.evaluate(() => window.atlasHarness.opens), [{ id: 2 }])
    await page.getByRole('button', { name: '放大地图', exact: true }).click()
    assert((await page.locator('.atlas-scene').getAttribute('transform')).includes('scale(1.25)'))
    const stage = await page.locator('.atlas-svg').boundingBox()
    await page.mouse.move(stage.x + 40, stage.y + 40)
    await page.mouse.down()
    await page.mouse.move(stage.x + 110, stage.y + 80)
    await page.mouse.up()
    assert(!(await page.locator('.atlas-scene').getAttribute('transform')).startsWith('translate(0 0)'))
    await page.getByRole('button', { name: '查看全图', exact: true }).click()
    assert((await page.locator('.atlas-scene').getAttribute('transform')).startsWith('translate(0 0)'))

    await page.getByRole('button', { name: '从家出发', exact: true }).click()
    await page.locator('.atlas-home-dialog').waitFor()
    const homeSearch = page.locator('.atlas-home-dialog').getByRole('combobox', { name: '搜索城市或省份', exact: true })
    await homeSearch.fill('广州')
    await page.locator('.atlas-home-dialog .city-results').getByRole('option').filter({ hasText: '广州市' }).first().click()
    await page.getByLabel('家的地点名称', { exact: true }).fill(origin.location_name)
    await page.getByLabel('家的纬度', { exact: true }).fill(String(origin.latitude))
    await page.getByLabel('家的经度', { exact: true }).fill(String(origin.longitude))
    await page.getByRole('button', { name: '保存出发地点', exact: true }).click()
    await page.locator('.atlas-home-dialog').waitFor({ state: 'hidden' })
    assert.equal(await page.locator('.atlas-home-marker').count(), 1)
    assert.equal(await page.locator('.atlas-route').count(), 4)
    await page.getByRole('button', { name: '全部足迹', exact: true }).click()
    assert.equal(await page.locator('.atlas-route').count(), 11)
    assert.equal(await page.locator('.atlas-plane').count(), 11)
    assert.equal(await page.locator('.atlas-plane circle').count(), 0)
    assert.equal(await page.locator('.atlas-city').count(), 11)
    assert.equal(await page.locator('.atlas-stats dd').first().textContent(), '12座')
    const starts = await page.locator('.atlas-route-base').evaluateAll(elements => elements.map(element => element.getAttribute('d').split(' Q')[0]))
    assert.equal(new Set(starts).size, 1)
    assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem('shiguangji-footprint-home-101'))), origin)
    if (process.env.ATLAS_SCREENSHOT_DIR) {
      await page.screenshot({ path: path.join(process.env.ATLAS_SCREENSHOT_DIR, '足迹地图-从家出发-Web.png'), fullPage: true })
    }
    await page.getByRole('button', { name: '本月旅程', exact: true }).click()
    await page.locator('.atlas-journey-cards button').filter({ hasText: '5月行记' }).click()
    assert.equal(await page.locator('.atlas-route').count(), 3)
    await page.getByRole('button', { name: '按日期连线', exact: true }).click()
    assert.equal(await page.locator('.atlas-route').count(), 1)
    assert.equal(await page.locator('.atlas-home-marker').count(), 0)
    await page.getByRole('button', { name: '从家出发', exact: true }).click()
    assert.equal(await page.locator('.atlas-route').count(), 3)
    assert.equal(await page.locator('.atlas-home-dialog').isVisible(), false)
    await page.locator('.atlas-home-setting').click()
    await page.getByLabel('家的纬度', { exact: true }).fill('91')
    assert.equal(await page.getByLabel('家的纬度', { exact: true }).evaluate(element => element.checkValidity()), false)
    await page.getByRole('button', { name: '取消', exact: true }).click()
    assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem('shiguangji-footprint-home-101'))), origin)
    await mount(page)
    await page.getByRole('button', { name: '从家出发', exact: true }).click()
    assert.equal(await page.locator('.atlas-route').count(), 11)
    assert.equal(await page.locator('.atlas-home-dialog').isVisible(), false)
    await page.evaluate(() => { window.atlasHarness.userId.value = 202 })
    await page.locator('.atlas-home-prompt').waitFor()
    assert.equal(await page.locator('.atlas-home-marker').count(), 0)
    assert.equal(await page.locator('.atlas-route').count(), 0)
    await page.evaluate(() => { window.atlasHarness.userId.value = 101 })
    await page.locator('.atlas-home-marker').waitFor()
    assert.equal(await page.locator('.atlas-route').count(), 11)
    await page.setViewportSize({ width: 390, height: 844 })
    await page.waitForTimeout(120)
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'home mode on narrow browser')
    await page.locator('.atlas-home-setting').click()
    const dialogBox = await page.locator('.atlas-home-dialog').boundingBox()
    assert(dialogBox.x >= 0 && dialogBox.x + dialogBox.width <= 390, 'home dialog fits narrow browser')
    const narrowSearch = page.locator('.atlas-home-dialog').getByRole('combobox', { name: '搜索城市或省份', exact: true })
    await narrowSearch.fill('北京')
    await page.locator('.atlas-home-dialog .city-results').getByRole('option').first().waitFor()
    await narrowSearch.press('Escape')
    assert.equal(await page.locator('.atlas-home-dialog').isVisible(), true, 'Escape closes city options before home settings')
    await narrowSearch.press('Escape')
    await page.locator('.atlas-home-dialog').waitFor({ state: 'hidden' })
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.locator('.atlas-home-setting').click()
    await page.getByRole('button', { name: '清除家的位置', exact: true }).click()
    await page.locator('.atlas-home-prompt').waitFor()
    assert.equal(await page.evaluate(() => localStorage.getItem('shiguangji-footprint-home-101')), null)
    await page.getByRole('button', { name: '按日期连线', exact: true }).click()

    for (const width of [1920, 1440, 768, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1080 })
      await page.getByRole('button', { name: '全部足迹', exact: true }).click()
      await page.waitForTimeout(120)
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow at ${width}`)
      const mapBox = await page.locator('.atlas-map-panel').boundingBox()
      const sideBox = await page.locator('.atlas-journey-panel').boundingBox()
      if (width >= 1440) assert(sideBox.x >= mapBox.x + mapBox.width, `desktop columns at ${width}`)
      if (width === 390) assert(sideBox.y >= mapBox.y + mapBox.height, 'narrow browser layout')
    }
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.waitForFunction(() => document.querySelector('.atlas-flow-control')?.getAttribute('aria-checked') === 'false')
    assert.equal(await page.getByRole('switch', { name: '轨迹流动动画' }).getAttribute('aria-checked'), 'false')
    assert.equal(await page.locator('.atlas-svg').evaluate(element => element.animationsPaused()), true)
    await page.evaluate(() => { window.atlasHarness.records.value = [] })
    await page.locator('.atlas-empty').waitFor()
    assert.equal(await page.locator('.atlas-city').count(), 0)
    await page.evaluate(data => { window.atlasHarness.records.value = [data[0], { ...data[0], id: 99 }] }, posts)
    await page.waitForFunction(() => document.querySelector('.atlas-stats dd')?.textContent === '1座')
    assert.equal(await page.locator('.atlas-route').count(), 0)
    assert.equal(await page.locator('.footprint-list button').count(), 2)
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.evaluate(() => { window.atlasHarness.picking.value = true })
    await page.locator('.footprint-map.picking .leaflet-overlay-pane path').first().waitFor()
    const search = page.getByRole('combobox', { name: '搜索城市或省份', exact: true })
    await search.fill('成都')
    await page.locator('.city-results').getByRole('option').first().click()
    assert((await page.getByLabel('地点名称', { exact: true }).inputValue()).includes('成都'))
    assert(Number(await page.getByLabel('纬度', { exact: true }).inputValue()) > 30)
    await page.getByRole('button', { name: '清除地点', exact: true }).click()
    assert.equal(await page.evaluate(() => window.atlasHarness.location.value), null)
    assert.deepEqual(errors, [])
    console.log('Footprint atlas checks passed: province geometry, city deduplication, chronological routes, home-origin branches and filters, home search and validation, account-isolated persistence and clearing, animated aircraft movement and rotation, pause and speed, record access, zoom and pan, responsive layouts, reduced motion, empty state and existing location picker.')
  } finally {
    await browser.close()
  }
}

main().catch(error => { console.error(error); process.exitCode = 1 })
