export function fmtBytes(n) {
  if (n == null) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

export function fmtDuration(s) {
  if (s == null) return ''
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

export function fmtDateTime(s) {
  if (!s) return ''
  return String(s).replace('T', ' ').slice(0, 16)
}

export function todayISO() {
  return new Date().toISOString().slice(0, 10)
}
