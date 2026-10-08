const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const assert = require('node:assert/strict')
const path = require('node:path')
const base = 'http://127.0.0.1:5173'
async function json(response) {
  assert(response.ok(), await response.text())
  return response.json()
}
async function main() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
  })
  const failures = []
  const circles = []
  try {
    const user = await json(
      await context.request.post(base + '/api/auth/register', {
        data: {
          username: 'profile_' + Date.now(),
          password: 'testpass1234',
          nickname: '拾光旅人',
        },
      }),
    )
    context.testUser = user
    for (const name of ['家人与日常', '云南同行']) {
      circles.push(
        await json(
          await context.request.post(base + '/api/circles', { data: { name } }),
        ),
      )
    }
    const circle = circles[1]
    const line = await json(
      await context.request.post(`${base}/api/circles/${circle.id}/lines`, {
        data: { title: '洱海之旅', kind: 'travel' },
      }),
    )
    const album = await json(
      await context.request.post(`${base}/api/circles/${circle.id}/albums`, {
        data: { title: '洱海影集', line_id: line.id },
      }),
    )
    const fs = require('node:fs')
    const post = await json(
      await context.request.post(`${base}/api/circles/${circle.id}/posts`, {
        multipart: {
          content: '一路向南，风从湖面吹来。',
          event_date: '2025-08-02',
          album_id: String(album.id),
          latitude: '25.6065',
          longitude: '100.2676',
          location_name: '大理',
          files: {
            name: 'friends.jpg',
            mimeType: 'image/jpeg',
            buffer: fs.readFileSync(
              path.resolve(
                __dirname,
                '../frontend/user/public/preview-assets/friends.jpg',
              ),
            ),
          },
        },
      }),
    )
    const page = await context.newPage()
    page.on('pageerror', (e) => failures.push(e.message))
    page.on('console', (m) => {
      if (m.type() === 'warning' && m.text().includes('[Vue warn]'))
        failures.push(m.text())
    })
    await page.goto(base)
    await page
      .getByRole('button', { name: '个人主页', exact: true })
      .filter({ visible: true })
      .click()
    await page.locator('.profile-page [data-action="post_create"]').waitFor()
    assert((await page.locator('.profile-page .line-tree').count()) === 0)
    assert(
      (
        await page
          .locator('[data-action="post_create"] .activity-circle')
          .textContent()
      ).includes('云南同行'),
    )
    assert((await page.locator('.activity-events li').count()) === 5)
    await page.locator('[data-action="post_create"] button').click()
    await page.locator('.record-original.ready').waitFor()
    await page.getByRole('button', { name: '编辑记录', exact: true }).click()
    assert(
      (
        await page
          .locator('.record-edit')
          .getByLabel('主题分册', { exact: true })
          .textContent()
      ).includes('洱海影集'),
    )
    assert(
      (
        await page
          .locator('.record-edit')
          .getByLabel('时间线', { exact: true })
          .textContent()
      ).includes('洱海之旅'),
    )
    await page.keyboard.press('Escape')
    await page
      .locator('.confirm-card')
      .getByRole('button', { name: '放弃修改', exact: true })
      .click()
    await page.locator('.record-backdrop').waitFor({ state: 'hidden' })
    assert(
      await page
        .locator('[data-action="post_create"] button')
        .first()
        .evaluate((el) => el === document.activeElement),
    )
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 960 })
      await page.locator('.body-grid').evaluate((el) => (el.scrollTop = 0))
      await page.waitForTimeout(350)
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `overflow ${width}`,
      )
      await page.screenshot({
        path: path.resolve(
          __dirname,
          `../.shots/2026-10-01-profile-${width}.png`,
        ),
      })
    }
    await page
      .getByLabel('筛选操作所属圈子')
      .selectOption(String(circles[0].id))
    await page.locator('.activity-events li').waitFor()
    assert((await page.locator('.activity-events li').count()) === 1)
    await page.getByLabel('筛选操作类型').selectOption('post')
    await page
      .locator('.profile-page .empty-state')
      .filter({ hasText: '没有符合筛选条件' })
      .waitFor()
    await page
      .getByLabel('筛选操作所属圈子')
      .selectOption({ label: '全部圈子' })
    await page.locator('[data-action="post_create"]').waitFor()
    await page.locator('.mobile-nav [data-view="timeline"]').click()
    await page.locator('.line-tree').waitFor()
    await page.locator('.mobile-top .profile-entry').click()
    await page.locator('[data-action="post_create"]').waitFor()
    assert((await page.getByLabel('筛选操作类型').inputValue()) === 'post')
    await page.getByLabel('筛选操作类型').selectOption('')
    await page.locator('[data-action="line_create"]').waitFor()
    await page.locator('[data-action="post_create"] button').click()
    await page.locator('.record-original.ready').waitFor()
    await page.getByRole('button', { name: '编辑记录', exact: true }).click()
    await page
      .locator('.record-edit')
      .getByLabel('记录内容', { exact: true })
      .fill('更新回忆')
    await page.getByRole('button', { name: '保存修改', exact: true }).click()
    await page
      .locator('.record-content')
      .filter({ hasText: '更新回忆' })
      .waitFor()
    await page.keyboard.press('Escape')
    await page.locator('.record-backdrop').waitFor({ state: 'hidden' })
    await page.locator('[data-action="post_edit"]').waitFor()
    await page.locator('[data-action="post_edit"] button').click()
    await page.locator('.record-original.ready').waitFor()
    await page.getByRole('button', { name: '删除记录', exact: true }).click()
    await page
      .locator('.confirm-card')
      .getByRole('button', { name: '删除记录', exact: true })
      .click()
    await page.locator('.record-backdrop').waitFor({ state: 'hidden' })
    await page.locator('[data-action="post_delete"]').waitFor()
    assert(
      (await page
        .locator('.activity-events [aria-label="查看关联记录"]')
        .count()) === 0,
    )
    assert(
      (await context.request.get(`${base}/api/posts/${post.id}`)).status() ===
        404,
    )
    await page.route('**/api/me/timeline*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 350))
      await route.abort('failed')
    })
    await page.getByLabel('筛选操作类型').selectOption('post')
    await page.locator('.activity-skeleton').waitFor()
    await page
      .locator('.activity-timeline')
      .getByRole('button', { name: '重试', exact: true })
      .waitFor()
    await page.unroute('**/api/me/timeline*')
    await page
      .locator('.activity-timeline')
      .getByRole('button', { name: '重试', exact: true })
      .click()
    await page.locator('[data-action="post_delete"]').waitFor()
    await page.getByLabel('筛选操作类型').selectOption('')
    await page.locator('[data-action="circle_create"]').first().waitFor()
    for (let i = 0; i < 50; i++) {
      await json(
        await context.request.patch(
          `${base}/api/circles/${circle.id}/settings`,
          { data: { description: `分页验证 ${i}` } },
        ),
      )
    }
    await page.locator('.mobile-nav [data-view="timeline"]').click()
    await page.locator('.line-tree').waitFor()
    await page.locator('.mobile-top .profile-entry').click()
    await page.locator('[data-action="circle_edit"]').first().waitFor()
    assert((await page.locator('.activity-events li').count()) === 50)
    await page.getByRole('button', { name: '更早的足迹', exact: true }).click()
    await page.getByText('已到最早的足迹', { exact: true }).waitFor()
    assert((await page.locator('.activity-events li').count()) === 57)
    assert.deepEqual(failures, [])
    console.log(
      'Personal activity passed: operations, cross-circle editing, filters, desktop/tablet/mobile, navigation, focus, deletion retention, retry and pagination.',
    )
  } finally {
    for (const circle of circles.reverse())
      await context.request.delete(`${base}/api/circles/${circle.id}`)
    if (context.testUser) {
      const admin = await browser.newContext()
      await json(
        await admin.request.post(base + '/api/admin/auth/login', {
          data: { username: 'admin', password: 'admin123' },
        }),
      )
      await json(
        await admin.request.delete(
          `${base}/api/admin/users/${context.testUser.id}`,
          { data: { reason: '个人主页测试数据清理' } },
        ),
      )
      await admin.close()
    }
    await browser.close()
  }
}
main().catch((e) => {
  console.error(e)
  process.exitCode = 1
})
