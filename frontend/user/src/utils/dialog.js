const stack = []

export function activateDialog(element, close) {
  const previous = document.activeElement
  const bodyOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  const grid = document.querySelector('.body-grid')
  const oldOverflow = grid?.style.overflow
  if (grid) grid.style.overflow = 'hidden'
  element.setAttribute('role', 'dialog')
  element.setAttribute('aria-modal', 'true')
  element.tabIndex = -1
  const focusable = () =>
    [
      ...element.querySelectorAll(
        'button:not(:disabled), a[href], input:not(:disabled), select, textarea, [tabindex="0"]',
      ),
    ].filter((el) => el.getClientRects().length)
  const token = {}
  stack.push(token)
  queueMicrotask(() =>
    (focusable()[0] || element).focus({ preventScroll: true }),
  )
  function keydown(event) {
    if (stack.at(-1) !== token) return
    if (event.key === 'Escape') {
      if (event.target.closest('[role="combobox"][aria-expanded="true"]'))
        return
      event.preventDefault()
      event.stopImmediatePropagation()
      close()
    }
    if (event.key === 'Tab') {
      const items = focusable()
      const first = items[0] || element
      const last = items.at(-1) || element
      if (
        event.shiftKey &&
        (document.activeElement === first || document.activeElement === element)
      ) {
        event.preventDefault()
        last.focus()
      } else if (
        !event.shiftKey &&
        (document.activeElement === last || document.activeElement === element)
      ) {
        event.preventDefault()
        first.focus()
      }
    }
  }
  document.addEventListener('keydown', keydown, true)
  return () => {
    document.removeEventListener('keydown', keydown, true)
    document.body.style.overflow = bodyOverflow
    stack.splice(stack.indexOf(token), 1)
    if (grid) grid.style.overflow = oldOverflow || ''
    if (previous?.isConnected) previous.focus({ preventScroll: true })
  }
}

export const dialogDirective = {
  mounted(el, binding) {
    el._releaseDialog = activateDialog(
      el.querySelector('[data-dialog-panel]') || el.firstElementChild || el,
      binding.value,
    )
  },
  unmounted(el) {
    el._releaseDialog?.()
  },
}
