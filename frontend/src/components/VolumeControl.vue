<template>
  <div class="volume-control" role="toolbar" aria-label="Contrôle du volume">
    <button
      type="button"
      class="volume-mute"
      :aria-pressed="musicMuted"
      :aria-label="muteLabel"
      :data-state="iconState"
      @click="onToggleMute"
    >
      <svg v-if="iconState === 'muted'" class="volume-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M4 9v6h4l5 4V5L8 9H4z"
          fill="currentColor"
          stroke="currentColor"
          stroke-width="1"
          stroke-linejoin="round"
        />
        <path
          d="M16 9l5 6M21 9l-5 6"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          fill="none"
        />
      </svg>
      <svg
        v-else-if="iconState === 'low'"
        class="volume-icon"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M4 9v6h4l5 4V5L8 9H4z"
          fill="currentColor"
          stroke="currentColor"
          stroke-width="1"
          stroke-linejoin="round"
        />
        <path
          d="M16 9c1.2 1 1.2 5 0 6"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          fill="none"
        />
      </svg>
      <svg v-else class="volume-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M4 9v6h4l5 4V5L8 9H4z"
          fill="currentColor"
          stroke="currentColor"
          stroke-width="1"
          stroke-linejoin="round"
        />
        <path
          d="M16 8c2 1.5 2 6.5 0 8"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          fill="none"
        />
        <path
          d="M19 5.5c3.5 2.5 3.5 10.5 0 13"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          fill="none"
        />
      </svg>
    </button>
    <input
      class="volume-slider"
      type="range"
      min="0"
      max="1"
      step="0.05"
      :value="music"
      :style="sliderStyle"
      aria-label="Volume musique"
      @input="onSlide"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useVolume } from '../composables/useVolume'

const { music, musicMuted, setMusic, toggleMusicMute } = useVolume()

const iconState = computed<'muted' | 'low' | 'high'>(() => {
  if (musicMuted.value) return 'muted'
  return music.value < 0.33 ? 'low' : 'high'
})

const muteLabel = computed(() => (musicMuted.value ? 'Activer le son' : 'Couper le son'))

const sliderStyle = computed(() => ({
  '--fill': `${(musicMuted.value ? 0 : music.value) * 100}%`,
}))

function onSlide(event: Event) {
  const target = event.target as HTMLInputElement
  setMusic(Number.parseFloat(target.value))
}

function onToggleMute() {
  toggleMusicMute()
}
</script>

<style scoped>
.volume-control {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.35rem 0.6rem 0.35rem 0.4rem;
  background: rgba(var(--color-white-rgb), 0.04);
  border: 1px solid rgba(var(--color-white-rgb), 0.1);
  border-radius: var(--radius-full);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.volume-mute {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  min-width: 48px;
  min-height: 48px;
  padding: 0;
  border-radius: 50%;
  background: rgba(var(--color-bg-rgb), 0.6);
  border: 1px solid rgba(var(--color-accent-rgb), 0.35);
  color: var(--color-accent);
  cursor: pointer;
  transition:
    box-shadow 0.18s var(--ease-smooth),
    border-color 0.18s var(--ease-smooth),
    transform 0.1s var(--ease-smooth),
    color 0.18s var(--ease-smooth);
}

.volume-mute:hover {
  border-color: rgba(var(--color-accent-rgb), 0.65);
  box-shadow: 0 0 18px rgba(var(--color-accent-rgb), 0.3);
}

.volume-mute:active {
  transform: scale(0.95);
}

.volume-mute:focus-visible {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(var(--color-accent-rgb), 0.4);
}

.volume-mute[data-state='muted'] {
  color: var(--color-error);
  border-color: rgba(var(--color-error-rgb), 0.55);
}

.volume-mute[data-state='muted']:hover {
  box-shadow: 0 0 18px rgba(var(--color-error-rgb), 0.35);
}

.volume-icon {
  width: 22px;
  height: 22px;
}

.volume-slider {
  -webkit-appearance: none;
  appearance: none;
  width: clamp(110px, 16vw, 180px);
  height: 28px;
  background: transparent;
  cursor: pointer;
  --fill: 80%;
}

.volume-slider:focus {
  outline: none;
}

.volume-slider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: var(--radius-full);
  background: linear-gradient(
    90deg,
    var(--color-primary) 0%,
    var(--color-accent) var(--fill),
    rgba(var(--color-white-rgb), 0.12) var(--fill),
    rgba(var(--color-white-rgb), 0.12) 100%
  );
  border: 1px solid rgba(var(--color-white-rgb), 0.08);
}

.volume-slider::-moz-range-track {
  height: 6px;
  border-radius: var(--radius-full);
  background: rgba(var(--color-white-rgb), 0.12);
  border: 1px solid rgba(var(--color-white-rgb), 0.08);
}

.volume-slider::-moz-range-progress {
  height: 6px;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-text);
  border: 2px solid var(--color-accent);
  margin-top: -7px;
  box-shadow:
    0 0 12px rgba(var(--color-accent-rgb), 0.6),
    0 0 4px rgba(var(--color-primary-rgb), 0.4);
  transition:
    transform 0.12s var(--ease-bounce),
    box-shadow 0.18s var(--ease-smooth);
}

.volume-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-text);
  border: 2px solid var(--color-accent);
  box-shadow:
    0 0 12px rgba(var(--color-accent-rgb), 0.6),
    0 0 4px rgba(var(--color-primary-rgb), 0.4);
}

.volume-slider:hover::-webkit-slider-thumb,
.volume-slider:focus-visible::-webkit-slider-thumb {
  transform: scale(1.15);
  box-shadow:
    0 0 18px rgba(var(--color-accent-rgb), 0.85),
    0 0 6px rgba(var(--color-primary-rgb), 0.6);
}

.volume-slider:focus-visible::-webkit-slider-thumb {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

@media (max-width: 899px) {
  .volume-slider {
    /* Taller hit area for thumbs; the 6px track stays centred in it. */
    height: 44px;
  }
}

@media (max-width: 560px) {
  .volume-slider {
    width: clamp(96px, 30vw, 140px);
  }
}
</style>
