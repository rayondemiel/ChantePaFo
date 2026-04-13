<template>
  <div class="answer-input-wrap">
    <input
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
    <div v-if="feedback" :key="feedbackKey" class="feedback-slot">
      <span :class="feedback.cls">{{ feedback.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import type { FuzzyResult } from '../types'

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

const inputRef = ref<HTMLInputElement | null>(null)
const text = ref('')
const feedback = ref<{ label: string; cls: string } | null>(null)
const feedbackKey = ref(0)
let clearHandle: ReturnType<typeof setTimeout> | null = null

function onSubmit() {
  const trimmed = text.value.trim()
  if (!trimmed) return
  emit('submit', trimmed)
  text.value = ''
}

function setResult(result: FuzzyResult) {
  if (clearHandle) {
    clearTimeout(clearHandle)
    clearHandle = null
  }
  if (result.bonus) {
    feedback.value = { label: 'Parfait !', cls: 'feedback-correct anim-correct-pop' }
  } else if (result.title_match) {
    feedback.value = { label: 'Trouvé !', cls: 'feedback-correct anim-correct-pop' }
  } else if (result.artist_match) {
    feedback.value = { label: 'Artiste ✓', cls: 'feedback-correct feedback-soft' }
  } else {
    feedback.value = { label: 'Raté...', cls: 'feedback-wrong anim-shake' }
  }
  feedbackKey.value += 1
  clearHandle = setTimeout(() => {
    feedback.value = null
    clearHandle = null
  }, 1500)
}

defineExpose({ setResult })

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
}

.input-answer {
  min-height: 48px;
  font-family: var(--font-body);
  font-size: var(--text-lg);
}

.feedback-slot {
  min-height: 1.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
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
  box-shadow: 0 0 18px rgba(var(--color-success-rgb), 0.35);
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
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
