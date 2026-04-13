import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmDialog from '../../src/components/ConfirmDialog.vue'

describe('ConfirmDialog', () => {
  it('renders nothing when the open prop is false', () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: false, title: 'Hello', message: 'World' },
    })
    expect(wrapper.find('dialog').exists()).toBe(false)
  })

  it('shows title and message when open', () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'Quitter ?', message: 'Vraiment ?' },
    })
    expect(wrapper.text()).toContain('Quitter ?')
    expect(wrapper.text()).toContain('Vraiment ?')
    expect(wrapper.find('dialog').exists()).toBe(true)
  })

  it('emits confirm when the confirm button is clicked', async () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'T', message: 'M', confirmText: 'Go' },
    })
    await wrapper.get('.btn-danger').trigger('click')
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('emits cancel when the cancel button is clicked', async () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'T', message: 'M' },
    })
    await wrapper.get('.btn-ghost').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('hides the cancel button when cancelText is empty', () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'T', message: 'M', cancelText: '' },
    })
    expect(wrapper.find('.btn-ghost').exists()).toBe(false)
    expect(wrapper.find('.btn-danger').exists()).toBe(true)
  })

  it('applies the danger variant class', () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'T', message: 'M', variant: 'danger' },
    })
    expect(wrapper.find('.modal-danger').exists()).toBe(true)
  })

  it('emits cancel when the dialog element itself receives a click (backdrop)', async () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'T', message: 'M' },
    })
    const dialog = wrapper.get('dialog')
    // The click target must be the dialog itself to count as a backdrop click.
    await dialog.trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('does not cancel when a click bubbles from the modal card', async () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'T', message: 'M' },
    })
    // Click on the title — bubbles up through .modal-card, target !== dialog
    await wrapper.get('.modal-title').trigger('click')
    expect(wrapper.emitted('cancel')).toBeUndefined()
  })

  it('emits cancel when the native close event fires (Escape key)', async () => {
    const wrapper = mount(ConfirmDialog, {
      props: { open: true, title: 'T', message: 'M' },
    })
    await wrapper.get('dialog').trigger('close')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
