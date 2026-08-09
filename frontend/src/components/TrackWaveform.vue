<template>
  <div
    class="track-waveform"
    role="progressbar"
    :aria-valuenow="Math.round(props.progress * 100)"
    aria-valuemin="0"
    aria-valuemax="100"
    :class="{ 'waveform-critical': props.stressLevel === 'critical' }"
  >
    <svg class="waveform-bars" viewBox="0 0 400 48" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="bar-gradient-filled" x1="0" y1="1" x2="0" y2="0">
          <stop class="gradient-stop-bottom" offset="0%" />
          <stop class="gradient-stop-top" offset="92%" />
          <stop class="gradient-stop-highlight" offset="100%" />
        </linearGradient>
        <linearGradient id="bar-gradient-critical" x1="0" y1="1" x2="0" y2="0">
          <stop class="gradient-stop-critical-bottom" offset="0%" />
          <stop class="gradient-stop-critical-top" offset="100%" />
        </linearGradient>
      </defs>
      <rect
        v-for="(bar, i) in bars"
        :key="i"
        :x="bar.x"
        :y="bar.y"
        :width="barWidth - 1"
        :height="bar.height"
        :class="[
          'waveform-bar',
          i < filledCount
            ? props.stressLevel === 'critical'
              ? 'bar-critical'
              : 'bar-filled'
            : 'bar-unfilled',
          { 'bar-animate': i < filledCount && !props.frozen },
        ]"
        :style="{ animationDelay: `${(i * 73) % 2000}ms` }"
        rx="2.5"
      />
    </svg>

    <!-- Playhead glow cone -->
    <div
      v-if="!props.frozen"
      class="playhead-glow"
      :style="{ left: `${props.progress * 100}%` }"
    ></div>
    <div v-if="!props.frozen" class="playhead" :style="{ left: `${props.progress * 100}%` }"></div>

    <div v-if="props.markers.length > 0" class="markers-layer">
      <span
        v-for="(marker, idx) in positionedMarkers"
        :key="idx"
        class="marker anim-correct-pop"
        :class="`marker-${marker.match_type}`"
        :style="{ left: `${marker.left}%` }"
        :title="marker.name"
        tabindex="0"
        :aria-label="`${marker.name} - ${marker.match_type}`"
      >
        <span class="marker-line" :class="`marker-line-${marker.match_type}`"></span>
        <span class="marker-tooltip">
          <span class="marker-tooltip-name">{{ marker.name }}</span>
          <span class="marker-tooltip-type">{{ marker.match_type }}</span>
        </span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAudio } from '../composables/useAudio'
import type { MatchInfo } from '../types'

const BAR_COUNT = 40

const props = withDefaults(
  defineProps<{
    progress?: number
    frozen?: boolean
    markers?: MatchInfo[]
    totalDurationMs?: number
    stressLevel?: 'normal' | 'warning' | 'critical'
  }>(),
  {
    progress: 0,
    frozen: false,
    markers: () => [],
    totalDurationMs: 25000,
    stressLevel: 'normal',
  },
)

const barWidth = 400 / BAR_COUNT

// Static fallback shape — used when frozen (reveal) or when the analyser has
// no signal (not connected, or CORS-tainted source zeroing the graph).
const STATIC_LEVELS = Array.from({ length: BAR_COUNT }, (_, i) => {
  const t = i / BAR_COUNT
  const raw =
    Math.sin(t * Math.PI * 2.7) * 0.25 +
    Math.sin(t * Math.PI * 5.3) * 0.15 +
    Math.sin(t * Math.PI * 11.1) * 0.1 +
    Math.cos(t * Math.PI * 3.2 + 1) * 0.2 +
    0.35
  return Math.max(0.15, Math.min(1, raw))
})

const { frequencyData } = useAudio()

// Live spectrum: bar i averages its share of the FFT bins (low → high across
// the width). Null means "no usable signal, draw the static shape".
const liveLevels = computed<number[] | null>(() => {
  if (props.frozen) return null
  const data = frequencyData.value
  if (data.length === 0) return null
  let energy = 0
  const levels = Array.from({ length: BAR_COUNT }, (_, i) => {
    // Log-frequency mapping: music packs its energy into the low FFT bins,
    // so a linear split lights a handful of left bars and leaves the rest
    // flat (looks broken). Exponentially wider ranges per bar give the
    // classic full-width equalizer read.
    const lo =
      i === 0 ? 0 : Math.min(data.length - 1, Math.floor(Math.pow(data.length, i / BAR_COUNT)))
    const hi = Math.max(
      lo + 1,
      Math.min(data.length, Math.ceil(Math.pow(data.length, (i + 1) / BAR_COUNT))),
    )
    const slice = data.subarray(lo, hi)
    let sum = 0
    slice.forEach((v) => {
      sum += v
    })
    const level = sum / (slice.length * 255)
    energy += level
    return level
  })
  return energy > 0 ? levels : null
})

// Music rolls off toward the treble — without compensation the right end of
// the strip stays flat. Gain ramps from 1× (bass) to 1 + HIGH_BOOST (treble).
const HIGH_BOOST = 2

const bars = computed(() => {
  const live = liveLevels.value
  const source = live ?? STATIC_LEVELS
  return source.map((level, i) => {
    let h: number
    if (live) {
      const tilt = 1 + HIGH_BOOST * Math.pow(i / (BAR_COUNT - 1), 1.2)
      const shaped = Math.min(1, level * tilt)
      // pow 0.8 keeps quiet bands visible without sqrt's blob-flattening
      // compression; the 0.1 floor keeps the strip alive between beats.
      h = (0.1 + 0.9 * Math.pow(shaped, 0.8)) * 48
    } else {
      h = level * 48
    }
    return {
      x: i * barWidth,
      y: 48 - h,
      height: h,
    }
  })
})

const filledCount = computed(() => {
  return Math.round(props.progress * BAR_COUNT)
})

const positionedMarkers = computed(() =>
  props.markers.map((m) => ({
    ...m,
    left: props.totalDurationMs > 0 ? (m.time_ms / props.totalDurationMs) * 100 : 0,
  })),
)
</script>

<style scoped>
.track-waveform {
  position: relative;
  width: 100%;
  height: 48px;
  border-radius: var(--radius-md);
  background: rgba(var(--color-surface-rgb), 0.5);
  border: 1px solid rgba(var(--color-accent-rgb), 0.08);
  overflow: visible;
  transition: box-shadow 0.3s var(--ease-smooth);
}

.waveform-critical {
  box-shadow: inset 0 0 30px rgba(var(--color-error-rgb), 0.15);
}

.waveform-bars {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

/* SVG gradient stops styled via CSS for design token compatibility */
.gradient-stop-bottom {
  stop-color: var(--color-primary);
  stop-opacity: 0.4;
}
.gradient-stop-top {
  stop-color: var(--color-accent);
  stop-opacity: 0.9;
}
.gradient-stop-highlight {
  stop-color: var(--color-text);
  stop-opacity: 0.05;
}
.gradient-stop-critical-bottom {
  stop-color: var(--color-error);
  stop-opacity: 0.5;
}
.gradient-stop-critical-top {
  stop-color: var(--color-error);
  stop-opacity: 0.95;
}

.waveform-bar {
  transition: fill 0.3s var(--ease-smooth);
}

.bar-filled {
  fill: url(#bar-gradient-filled);
}

.bar-critical {
  fill: url(#bar-gradient-critical);
  animation: bar-pulse-critical 0.6s ease-in-out infinite;
}

.bar-unfilled {
  fill: rgba(var(--color-white-rgb), 0.15);
  transition:
    fill 0.3s var(--ease-smooth),
    opacity 0.3s var(--ease-smooth);
}

.waveform-critical .bar-unfilled {
  animation: unfilled-pulse-red 1.2s ease-in-out infinite;
}

.bar-animate {
  /* Four beat periods per breathe cycle — the strip paces itself to the
     track's bpm (var synced by the ambiance store; ~2.4s at 100 bpm). */
  animation: bar-breathe calc(var(--ambiance-pulse-speed, 0.6s) * 4) ease-in-out infinite;
}

.bar-critical.bar-animate {
  animation:
    bar-breathe calc(var(--ambiance-pulse-speed, 0.6s) * 4) ease-in-out infinite,
    bar-pulse-critical 0.6s ease-in-out infinite;
}

@keyframes bar-breathe {
  0%,
  100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.06);
  }
}

@keyframes bar-pulse-critical {
  0%,
  100% {
    opacity: 0.85;
  }
  50% {
    opacity: 1;
  }
}

@keyframes unfilled-pulse-red {
  0%,
  100% {
    fill: rgba(var(--color-white-rgb), 0.1);
  }
  50% {
    fill: rgba(var(--color-error-rgb), 0.12);
  }
}

/* === Playhead === */
.playhead-glow {
  position: absolute;
  top: -4px;
  bottom: -4px;
  width: 30px;
  background: radial-gradient(
    ellipse at center,
    rgba(var(--color-accent-rgb), 0.3),
    transparent 70%
  );
  pointer-events: none;
  transition: left 0.2s linear;
  transform: translateX(-50%);
}

.playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--color-accent);
  box-shadow:
    0 0 8px rgba(var(--color-accent-rgb), 0.7),
    0 0 16px rgba(var(--color-accent-rgb), 0.3),
    -4px 0 8px rgba(var(--color-accent-rgb), 0.3);
  pointer-events: none;
  transition: left 0.2s linear;
}

/* === Markers === */
.markers-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.marker {
  position: absolute;
  top: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transform: translateX(-50%);
  pointer-events: auto;
  cursor: default;
  animation:
    correct-pop 0.5s var(--ease-bounce),
    marker-glow-pulse 2s ease-in-out infinite;
  z-index: 2;
}

.marker-bonus {
  background: var(--color-success);
  box-shadow: 0 0 8px rgba(var(--color-success-rgb), 0.7);
}

.marker-title {
  background: var(--color-accent);
  box-shadow: 0 0 8px rgba(var(--color-accent-rgb), 0.7);
}

.marker-artist {
  background: var(--color-warning);
  box-shadow: 0 0 8px rgba(var(--color-warning-rgb), 0.7);
}

.marker-line {
  position: absolute;
  top: 14px;
  left: 50%;
  width: 1px;
  height: 32px;
  opacity: 0.4;
  pointer-events: none;
}

.marker-line-bonus {
  background: var(--color-success);
}
.marker-line-title {
  background: var(--color-accent);
}
.marker-line-artist {
  background: var(--color-warning);
}

@keyframes marker-glow-pulse {
  0%,
  100% {
    filter: brightness(1);
  }
  50% {
    filter: brightness(1.3);
  }
}

/* === Marker tooltip === */
.marker-tooltip {
  position: absolute;
  top: -38px;
  left: 50%;
  transform: translateX(-50%) scale(0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 0.2rem 0.4rem;
  background: linear-gradient(135deg, var(--color-surface), var(--color-surface-hover));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 0.15s var(--ease-smooth),
    transform 0.15s var(--ease-smooth);
  z-index: 10;
}

.marker:hover > .marker-tooltip,
.marker:focus > .marker-tooltip {
  opacity: 1;
  transform: translateX(-50%) scale(1);
}

.marker-tooltip-name {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text);
}

.marker-tooltip-type {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: capitalize;
}

/* === Desktop height === */
@media (min-width: 900px) {
  .track-waveform {
    height: 64px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .bar-animate,
  .bar-critical {
    animation: none;
  }
  .marker {
    animation: none;
  }
  .waveform-critical .bar-unfilled {
    animation: none;
  }
}
</style>
