<template>
  <div
    class="circular-countdown"
    :class="{
      'countdown-warning': stressLevel === 'warning',
      'countdown-critical': stressLevel === 'critical',
      'digit-tick': digitTick && stressLevel === 'critical',
    }"
    role="timer"
    aria-live="polite"
    aria-label="Temps restant"
  >
    <svg class="ring" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
      <defs>
        <linearGradient :id="gradientId" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" :stop-color="gradientStart" />
          <stop offset="100%" :stop-color="gradientEnd" />
        </linearGradient>
      </defs>
      <circle class="ring-track" cx="32" cy="32" r="28" />
      <circle
        class="ring-progress"
        cx="32"
        cy="32"
        r="28"
        :stroke="`url(#${gradientId})`"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
      />
    </svg>
    <span class="value text-display" :class="{ 'value-critical': stressLevel === 'critical' }">{{
      displaySeconds
    }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    duration: number
    running?: boolean
    /** Seconds already elapsed when the timer starts (resume mid-round). */
    elapsed?: number
  }>(),
  { running: true, elapsed: 0 },
)

const emit = defineEmits<{
  finished: []
}>()

const circumference = 2 * Math.PI * 28
const remainingMs = ref(Math.max(0, props.duration * 1000 - Math.max(0, props.elapsed) * 1000))
const handle = ref<ReturnType<typeof globalThis.setInterval> | null>(null)
const digitTick = ref(false)
let startedAt = 0
let elapsedAtPause = 0
let finishedFired = false
let lastDisplaySecond = Math.ceil(remainingMs.value / 1000)
// Per-instance id so several countdowns on screen don't share a <linearGradient>.
const gradientId = `circular-countdown-gradient-${useId()}`

const displaySeconds = computed(() => Math.ceil(remainingMs.value / 1000))
const progress = computed(() => {
  const total = props.duration * 1000
  if (total <= 0) return 0
  return Math.max(0, Math.min(1, remainingMs.value / total))
})
const dashOffset = computed(() => circumference * (1 - progress.value))

const stressLevel = computed<'normal' | 'warning' | 'critical'>(() => {
  const sec = displaySeconds.value
  if (sec <= 5) return 'critical'
  if (sec <= 10) return 'warning'
  return 'normal'
})

const gradientStart = computed(() => {
  if (stressLevel.value === 'critical') return 'var(--color-error)'
  if (stressLevel.value === 'warning') return 'var(--color-warning)'
  return 'var(--color-primary)'
})

const gradientEnd = computed(() => {
  if (stressLevel.value === 'critical') return 'var(--color-error)'
  if (stressLevel.value === 'warning') return 'var(--color-primary)'
  return 'var(--color-accent)'
})

function stopInterval() {
  if (handle.value !== null) {
    globalThis.clearInterval(handle.value)
    handle.value = null
  }
}

function tick() {
  const total = props.duration * 1000
  const elapsed = elapsedAtPause + (Date.now() - startedAt)
  const next = Math.max(0, total - elapsed)
  remainingMs.value = next

  const currentSec = Math.ceil(next / 1000)
  if (currentSec !== lastDisplaySecond && stressLevel.value === 'critical') {
    digitTick.value = true
    globalThis.setTimeout(() => {
      digitTick.value = false
    }, 200)
  }
  lastDisplaySecond = currentSec

  if (next <= 0) {
    stopInterval()
    if (!finishedFired) {
      finishedFired = true
      emit('finished')
    }
  }
}

function startInterval() {
  stopInterval()
  finishedFired = false
  elapsedAtPause = Math.max(0, props.elapsed) * 1000
  remainingMs.value = Math.max(0, props.duration * 1000 - elapsedAtPause)
  startedAt = Date.now()
  lastDisplaySecond = Math.ceil(remainingMs.value / 1000)
  handle.value = globalThis.setInterval(tick, 100)
}

defineExpose({ stressLevel })

onMounted(() => {
  if (props.running) {
    startInterval()
  }
})

watch(
  () => props.running,
  (next) => {
    if (next) {
      startInterval()
    } else {
      stopInterval()
    }
  },
)

onBeforeUnmount(() => {
  stopInterval()
})
</script>

<style scoped>
.circular-countdown {
  position: relative;
  display: inline-flex;
  width: 64px;
  height: 64px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: box-shadow 0.3s var(--ease-smooth);
}

/* Pulsing outer ring for warning/critical */
.countdown-warning::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid rgba(var(--color-warning-rgb), 0.3);
  animation: outer-ring-pulse 1.5s ease-in-out infinite;
}

.countdown-critical {
  animation: countdown-shake 0.12s ease-in-out infinite;
  box-shadow: 0 0 30px rgba(var(--color-error-rgb), 0.6);
}

.countdown-critical::after {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 2px solid rgba(var(--color-error-rgb), 0.5);
  animation: outer-ring-pulse-critical 0.8s ease-in-out infinite;
}

.digit-tick .value {
  transform: scale(1.15);
}

.ring {
  transform: rotate(-90deg);
}

.ring-track {
  fill: none;
  stroke: rgba(var(--color-white-rgb), 0.08);
  stroke-width: 5;
}

.ring-progress {
  fill: none;
  stroke-width: 5;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.18s var(--ease-smooth);
  filter: drop-shadow(0 0 6px rgba(var(--color-primary-rgb), 0.55));
}

.value {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--color-text);
  text-shadow:
    0 0 12px rgba(var(--color-accent-rgb), 0.55),
    0 0 24px rgba(var(--color-accent-rgb), 0.2);
  transition: transform 0.15s var(--ease-bounce);
}

.value-critical {
  color: var(--color-error);
  text-shadow:
    0 0 12px rgba(var(--color-error-rgb), 0.7),
    0 0 24px rgba(var(--color-error-rgb), 0.3);
  filter: drop-shadow(0 0 8px rgba(var(--color-error-rgb), 0.5));
}

@keyframes countdown-shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-1.5px) rotate(-1.5deg);
  }
  75% {
    transform: translateX(1.5px) rotate(1.5deg);
  }
}

@keyframes outer-ring-pulse {
  0%,
  100% {
    opacity: 0.3;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.05);
  }
}

@keyframes outer-ring-pulse-critical {
  0%,
  100% {
    opacity: 0.4;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.08);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ring-progress {
    transition: none;
  }
  .countdown-critical {
    animation: none;
  }
  .countdown-warning::after,
  .countdown-critical::after {
    animation: none;
  }
}

@media (min-width: 768px) {
  .circular-countdown {
    width: 88px;
    height: 88px;
  }
}
</style>
