<template>
  <div class="countdown">
    <span :key="current" class="countdown-digit text-display anim-countdown-pop">
      {{ current }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = withDefaults(
  defineProps<{
    from?: number
    intervalMs?: number
  }>(),
  {
    from: 3,
    intervalMs: 1000,
  },
)

const emit = defineEmits<{
  done: []
}>()

const current = ref(props.from)
let handle: ReturnType<typeof globalThis.setInterval> | null = null
let doneFired = false

function stop() {
  if (handle !== null) {
    globalThis.clearInterval(handle)
    handle = null
  }
}

onMounted(() => {
  handle = globalThis.setInterval(() => {
    if (current.value > 0) {
      current.value -= 1
    }
    if (current.value <= 0 && !doneFired) {
      doneFired = true
      stop()
      emit('done')
    }
  }, props.intervalMs)
})

onBeforeUnmount(() => {
  stop()
})
</script>

<style scoped>
.countdown {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
}

.countdown-digit {
  font-size: 6rem;
  line-height: 1;
  color: var(--color-text);
  text-shadow:
    0 0 30px rgba(var(--color-primary-rgb), 0.6),
    0 0 60px rgba(var(--color-secondary-rgb), 0.45),
    0 0 90px rgba(var(--color-accent-rgb), 0.25);
  background: linear-gradient(
    135deg,
    var(--color-primary),
    var(--color-secondary),
    var(--color-accent)
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

@media (min-width: 768px) {
  .countdown-digit {
    font-size: 8rem;
  }
}
</style>
