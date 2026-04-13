import { describe, it, expect, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AnswerInput from '../../src/components/AnswerInput.vue'
import type { FuzzyResult } from '../../src/types'

describe('AnswerInput', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders an input with the default placeholder', () => {
    const wrapper = mount(AnswerInput)
    const input = wrapper.get('input.input-answer')
    expect(input.attributes('placeholder')).toBe('Titre ou artiste...')
  })

  it('accepts a custom placeholder', () => {
    const wrapper = mount(AnswerInput, { props: { placeholder: 'Devine...' } })
    expect(wrapper.get('input').attributes('placeholder')).toBe('Devine...')
  })

  it('emits submit with trimmed text on enter', async () => {
    const wrapper = mount(AnswerInput)
    const input = wrapper.get('input')
    await input.setValue('  Beat It  ')
    await input.trigger('keydown.enter')
    const emitted = wrapper.emitted('submit')
    expect(emitted).toBeDefined()
    expect(emitted![0]).toEqual(['Beat It'])
  })

  it('does not emit on empty input', async () => {
    const wrapper = mount(AnswerInput)
    const input = wrapper.get('input')
    await input.setValue('   ')
    await input.trigger('keydown.enter')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('clears the input after successful submit', async () => {
    const wrapper = mount(AnswerInput)
    const input = wrapper.get('input')
    await input.setValue('Thriller')
    await input.trigger('keydown.enter')
    expect((input.element as HTMLInputElement).value).toBe('')
  })

  it('disables the input when disabled prop is true', () => {
    const wrapper = mount(AnswerInput, { props: { disabled: true } })
    expect((wrapper.get('input').element as HTMLInputElement).disabled).toBe(true)
  })

  it('auto-focuses the input on mount', () => {
    const wrapper = mount(AnswerInput, { attachTo: document.body })
    expect(document.activeElement).toBe(wrapper.get('input').element)
    wrapper.unmount()
  })

  it('shows "Parfait !" when bonus is true via setResult', async () => {
    const wrapper = mount(AnswerInput)
    const result: FuzzyResult = {
      title_match: true,
      artist_match: true,
      bonus: true,
      distance: 0,
    }
    ;(wrapper.vm as unknown as { setResult: (r: FuzzyResult) => void }).setResult(result)
    await wrapper.vm.$nextTick()
    const fb = wrapper.get('.feedback-correct')
    expect(fb.text()).toContain('Parfait')
    expect(fb.classes()).toContain('anim-correct-pop')
  })

  it('shows "Trouvé !" for title match only', async () => {
    const wrapper = mount(AnswerInput)
    ;(wrapper.vm as unknown as { setResult: (r: FuzzyResult) => void }).setResult({
      title_match: true,
      artist_match: false,
      bonus: false,
      distance: 1,
    })
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.feedback-correct').text()).toContain('Trouvé')
  })

  it('shows "Artiste" for artist match only', async () => {
    const wrapper = mount(AnswerInput)
    ;(wrapper.vm as unknown as { setResult: (r: FuzzyResult) => void }).setResult({
      title_match: false,
      artist_match: true,
      bonus: false,
      distance: 1,
    })
    await wrapper.vm.$nextTick()
    const fb = wrapper.get('.feedback-correct')
    expect(fb.text()).toContain('Artiste')
  })

  it('shows "Raté..." with shake for no match', async () => {
    const wrapper = mount(AnswerInput)
    ;(wrapper.vm as unknown as { setResult: (r: FuzzyResult) => void }).setResult({
      title_match: false,
      artist_match: false,
      bonus: false,
      distance: 9,
    })
    await wrapper.vm.$nextTick()
    const fb = wrapper.get('.feedback-wrong')
    expect(fb.text()).toContain('Raté')
    expect(fb.classes()).toContain('anim-shake')
  })

  it('clears the feedback after 1500ms', async () => {
    vi.useFakeTimers()
    const wrapper = mount(AnswerInput)
    ;(wrapper.vm as unknown as { setResult: (r: FuzzyResult) => void }).setResult({
      title_match: true,
      artist_match: true,
      bonus: true,
      distance: 0,
    })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.feedback-correct').exists()).toBe(true)
    vi.advanceTimersByTime(1500)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.feedback-correct').exists()).toBe(false)
  })
})
