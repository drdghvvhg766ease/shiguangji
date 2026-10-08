import { createVNode, render } from 'vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

/**
 * Promise 化确认框，替代原生 confirm。
 * confirmDialog({ title, message, confirmText, danger }) -> Promise<boolean>
 */
export function confirmDialog(options = {}) {
  return new Promise((resolve) => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    const close = (result) => {
      render(null, container)
      container.remove()
      resolve(result)
    }

    const vnode = createVNode(ConfirmDialog, {
      ...options,
      onConfirm: () => close(true),
      onCancel: () => close(false),
    })
    render(vnode, container)
  })
}
