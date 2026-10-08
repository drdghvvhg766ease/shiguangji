const fs = require('node:fs')
const path = require('node:path')
const postcss = require('../frontend/user/node_modules/postcss')
const file = path.resolve(__dirname, '../frontend/user/src/styles.css')
const root = postcss.parse(fs.readFileSync(file, 'utf8'))
const obsolete = /\.(?:post(?:-[\w-]+)?|photo-grid-[\w-]+|polaroid|masonry|m-[\w-]+|timeline-[\w-]+|feed-hero(?:-[\w-]+)?|hero-date|vertical-note|skeleton-(?:post|head|avatar|lines|line|photo))(?![\w-])|#feed-posts/
let removed = 0
root.walkRules(rule => {
  const selectors = rule.selectors.filter(selector => !obsolete.test(selector))
  if (!selectors.length) { rule.remove(); removed++ }
  else rule.selectors = selectors
})
root.walkDecls('letter-spacing', declaration => { declaration.value = '0' })
root.walkAtRules('media', rule => { if (!rule.nodes.some(node => node.type !== 'comment')) rule.remove() })
fs.writeFileSync(file, root.toString())
console.log(`Removed ${removed} obsolete style rules`)
