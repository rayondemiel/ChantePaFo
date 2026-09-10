<template>
  <div class="answer-input-wrap">
    <label class="sr-only" :for="inputId">{{ placeholder }}</label>
    <input
      :id="inputId"
      ref="inputRef"
      v-model="text"
      type="text"
      class="input-answer"
      :placeholder="placeholder"
      :disabled="disabled"
      autocomplete="off"
      autocapitalize="off"
      autocorrect="off"
      spellcheck="false"
      @keydown.enter="onSubmit"
    />
    <div v-if="displayFeedback" :key="feedbackKey" class="feedback-slot">
      <span :class="displayFeedback.cls">{{ displayFeedback.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, useId } from 'vue'
import type { FuzzyResult } from '../types'

interface Feedback {
  label: string
  cls: string
}

withDefaults(
  defineProps<{
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    placeholder: 'Titre ou artiste...',
    disabled: false,
  },
)

const emit = defineEmits<{
  submit: [text: string]
}>()

const inputId = `answer-input-${useId()}`
const inputRef = ref<HTMLInputElement | null>(null)
const text = ref('')
const persistentFeedback = ref<Feedback | null>(null)
const flashFeedback = ref<Feedback | null>(null)
const feedbackKey = ref(0)
let clearHandle: ReturnType<typeof setTimeout> | null = null

const displayFeedback = computed(() => flashFeedback.value ?? persistentFeedback.value)

function onSubmit() {
  const trimmed = text.value.trim()
  if (!trimmed) return
  emit('submit', trimmed)
  text.value = ''
}

function resultToFeedback(result: FuzzyResult): Feedback {
  if (result.bonus) {
    return { label: 'Parfait !', cls: 'feedback-correct anim-correct-pop' }
  } else if (result.title_match) {
    return { label: 'Titre \u2713', cls: 'feedback-correct anim-correct-pop' }
  } else if (result.artist_match) {
    return { label: 'Artiste \u2713', cls: 'feedback-correct feedback-soft' }
  }
  return { label: 'Rat\u00e9...', cls: 'feedback-wrong anim-shake' }
}

function setResult(result: FuzzyResult) {
  if (clearHandle) {
    clearTimeout(clearHandle)
    clearHandle = null
  }

  const fb = resultToFeedback(result)

  if (result.bonus || result.title_match || result.artist_match) {
    persistentFeedback.value = fb
  }

  if (result.bonus || (!result.title_match && !result.artist_match)) {
    flashFeedback.value = fb
    feedbackKey.value += 1
    clearHandle = setTimeout(() => {
      flashFeedback.value = null
      clearHandle = null
    }, 1500)
  } else {
    feedbackKey.value += 1
  }
}

function clearResult() {
  persistentFeedback.value = null
  flashFeedback.value = null
  if (clearHandle) {
    clearTimeout(clearHandle)
    clearHandle = null
  }
}

defineExpose({ setResult, clearResult })

onMounted(() => {
  inputRef.value?.focus()
})

onBeforeUnmount(() => {
  if (clearHandle) clearTimeout(clearHandle)
})
</script>

<style scoped>
.answer-input-wrap {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--space-sm);
  position: relative;
}

.answer-input-wrap::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
  box-shadow: 0 0 12px rgba(var(--color-primary-rgb), 0.5);
  transition:
    width 0.3s var(--ease-smooth),
    left 0.3s var(--ease-smooth);
  pointer-events: none;
  border-radius: 1.5px;
}

.answer-input-wrap:focus-within::after {
  width: 100%;
  left: 0;
}

.input-answer {
  min-height: 48px;
  font-family: var(--font-body);
  font-size: var(--text-lg);
  border: 1px solid rgba(var(--color-accent-rgb), 0.15);
  transition:
    border-color 0.2s var(--ease-smooth),
    box-shadow 0.2s var(--ease-smooth);
}

.input-answer::placeholder {
  color: rgba(var(--color-white-rgb), 0.35);
}

.input-answer:focus {
  border-color: rgba(var(--color-accent-rgb), 0.5);
  box-shadow: 0 0 20px rgba(var(--color-accent-rgb), 0.15);
}

.feedback-slot {
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s var(--ease-smooth);
}

.feedback-slot .feedback-correct,
.feedback-slot .feedback-wrong {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  letter-spacing: 1px;
  padding: 0.4rem 1rem;
  border-radius: var(--radius-md);
}

.feedback-slot .feedback-correct {
  background: rgba(var(--color-success-rgb), 0.18);
  color: var(--color-success);
  box-shadow: 0 0 25px rgba(var(--color-success-rgb), 0.4);
}

.feedback-slot .feedback-soft {
  background: rgba(var(--color-accent-rgb), 0.14);
  color: var(--color-accent);
  box-shadow: 0 0 14px rgba(var(--color-accent-rgb), 0.25);
}

.feedback-slot .feedback-wrong {
  background: rgba(var(--color-error-rgb), 0.18);
  color: var(--color-error);
  box-shadow: 0 0 16px rgba(var(--color-error-rgb), 0.3);
}

.input-answer:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (min-width: 900px) {
  .input-answer {
    font-size: var(--text-xl);
    min-height: 52px;
  }
}
</style>
