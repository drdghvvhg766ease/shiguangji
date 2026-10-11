/**
 * 二十四节气（太阳黄经法，精度约 1 分钟）与连续记录天数工具。
 * 节气时刻按北京时间（UTC+8）判定，与国内日历习惯一致。
 */
const RAD = Math.PI / 180
const TERMS = [
  '小寒',
  '大寒',
  '立春',
  '雨水',
  '惊蛰',
  '春分',
  '清明',
  '谷雨',
  '立夏',
  '小满',
  '芒种',
  '夏至',
  '小暑',
  '大暑',
  '立秋',
  '处暑',
  '白露',
  '秋分',
  '寒露',
  '霜降',
  '立冬',
  '小雪',
  '大雪',
  '冬至',
]
const dayMs = 86400000
const toJD = (date) => date.getTime() / dayMs + 2440587.5
const fromJD = (jd) => new Date((jd - 2440587.5) * dayMs)

// 太阳视黄经（未取模，逐年单调递增，便于二分）
function sunLongitude(jd) {
  const t = (jd - 2451545.0) / 36525
  const mean = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
  const g =
    ((357.52911 + 35999.05029 * t - 0.0001537 * t * t) % 360) * RAD
  return (
    mean +
    1.914602 * Math.sin(g) +
    0.019993 * Math.sin(2 * g) +
    0.000289 * Math.sin(3 * g)
  )
}

const pad = (n) => String(n).padStart(2, '0')
const cache = new Map()

/** 某年 24 个节气对应的北京时间日期字符串 */
function termsOfYear(year) {
  const hit = cache.get(year)
  if (hit) return hit
  const lo0 = toJD(new Date(Date.UTC(year, 0, 3)))
  const hi0 = toJD(new Date(Date.UTC(year, 11, 28)))
  // 小寒太阳黄经 285°，取不早于年初的第一个 285° 连续值作为基准
  const first = 285 + 360 * Math.ceil((sunLongitude(lo0) - 285) / 360)
  const list = []
  for (let n = 0; n < 24; n += 1) {
    const target = first + n * 15
    let left = lo0
    let right = hi0
    for (let i = 0; i < 42; i += 1) {
      const mid = (left + right) / 2
      if (sunLongitude(mid) < target) left = mid
      else right = mid
    }
    const bj = new Date(fromJD((left + right) / 2).getTime() + 8 * 3600 * 1000)
    list.push(
      `${bj.getUTCFullYear()}-${pad(bj.getUTCMonth() + 1)}-${pad(bj.getUTCDate())}`,
    )
  }
  cache.set(year, list)
  return list
}

/** '2026-09-07' -> { name: '白露', index: 16 }，非节气返回 null */
export function solarTerm(dateStr) {
  const year = Number(dateStr.slice(0, 4))
  if (!year) return null
  const index = termsOfYear(year).indexOf(dateStr)
  return index < 0 ? null : { name: TERMS[index], index }
}

/** 某天是否节气当天 */
export function isTermStart(dateStr) {
  const year = Number(dateStr.slice(0, 4))
  if (!year) return false
  return termsOfYear(year).includes(dateStr)
}

const dayDiff = (a, b) =>
  Math.round(
    (Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / dayMs,
  )

/**
 * 连续记录天数：传入日期字符串数组（任意顺序），返回
 * { map: { 日期: 该日所在连续段天数 }, longest, longestFrom }
 */
export function streakInfo(dateStrings) {
  const sorted = [...new Set(dateStrings)].sort()
  const map = {}
  let longest = 0
  let longestFrom = ''
  let run = 1
  for (let i = 0; i < sorted.length; i += 1) {
    if (i > 0 && dayDiff(sorted[i - 1], sorted[i]) === 1) run += 1
    else run = 1
    map[sorted[i]] = run
    if (run > longest) {
      longest = run
      longestFrom = sorted[i]
    }
  }
  return { map, longest, longestFrom }
}