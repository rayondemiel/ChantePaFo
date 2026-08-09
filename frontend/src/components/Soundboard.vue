<template>
  <div class="soundboard" role="group" aria-label="Soundboard">
    <button
      v-for="s in SOUNDS"
      :key="s.id"
      type="button"
      class="sound-btn"
      :class="{
        'sound-btn-glow': glowing === s.id,
        'sound-btn-recharging': recharging === s.id,
      }"
      :data-test="`sound-${s.id}`"
      :aria-disabled="recharging === s.id ? 'true' : undefined"
      :aria-label="`Jouer ${s.label}`"
      @click="trigger(s.id)"
    >
      <span aria-hidden="true">{{ s.emoji }}</span>
      {{ s.label }}
    </button>
  </div>
  <!-- Attributed event capsule: who × what, in one stable glanceable spot.
       Permanently mounted so aria-live announcements are reliable. -->
  <div
    class="event-capsule"
    :class="{ 'event-capsule--visible': capsule }"
    :style="capsule ? { '--hue': String(capsule.hue) } : undefined"
    data-test="event-capsule"
    aria-live="polite"
  >
    <template v-if="capsule">
      <span class="capsule-dot" aria-hidden="true"></span>
      <span class="capsule-name">{{ capsule.name }}</span>
      <span class="capsule-emoji" aria-hidden="true">{{ capsule.emoji }}</span>
      <span class="capsule-label">{{ capsule.label }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useSocket } from '../composables/useSocket'
import { useRoomStore } from '../stores/room'
import { getPlayerHue } from '../lib/playerHue'

// Ids mirror the backend AllowedSound allowlist (payloads.py) and the files
// under public/sounds/.
const SOUNDS = [
  { id: 'applause', emoji: '👏', label: 'Applaudir' },
  { id: 'boo', emoji: '👎', label: 'Huées' },
  { id: 'drumroll', emoji: '🥁', label: 'Roulement' },
  { id: 'buzzer', emoji: '❌', label: 'Buzzer' },
  { id: 'airhorn', emoji: '📯', label: 'Airhorn' },
] as const

const COOLDOWN_MS = 1200
const GLOW_MS = 800
const CAPSULE_MS = 1400

// Sound you can feel while the mp3 files haven't shipped (and after, too).
const VIBRATIONS: Record<string, number[]> = {
  applause: [20, 40, 20, 40, 20],
  boo: [80],
  drumroll: [15, 30, 15, 30, 15, 30, 15],
  buzzer: [120],
  airhorn: [40, 60, 40, 60, 80],
}

const { emit, on, off } = useSocket()
const roomStore = useRoomStore()

const cooldown = ref(false)
// Which chip shows the recharge treatment — only the pressed one; the rest
// of the board must never look dead (the old all-chips :disabled read as
// "feature broken" on every press).
const recharging = ref<string | null>(null)
const glowing = ref<string | null>(null)
const capsule = ref<{ name: string; emoji: string; label: string; hue: number } | null>(null)
const audioCache = new Map<string, HTMLAudioElement>()
let glowTimer: ReturnType<typeof setTimeout> | null = null
let capsuleTimer: ReturnType<typeof setTimeout> | null = null

function trigger(sound: string): void {
  const code = roomStore.room?.code
  if (!code || cooldown.value) return
  cooldown.value = true
  recharging.value = sound
  setTimeout(() => {
    cooldown.value = false
    recharging.value = null
  }, COOLDOWN_MS)
  // Playback happens in onSoundboardPlayed for everyone — including the
  // sender via the room echo — so all phones stay roughly in sync and the
  // sound never double-plays locally.
  emit('soundboard', { code, sound })
}

function onSoundboardPlayed(data: unknown): void {
  const d = data as { player_id?: string; player_name?: string; sound?: string }
  if (!d?.sound) return

  let audio = audioCache.get(d.sound)
  if (!audio) {
    audio = new Audio(`/sounds/${d.sound}.mp3`)
    audioCache.set(d.sound, audio)
  }
  audio.currentTime = 0
  // Missing/placeholder file or autoplay refusal → stay silent, the capsule
  // and glow below still tell everyone the sound was triggered.
  audio.play()?.catch?.(() => {})

  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    navigator.vibrate(VIBRATIONS[d.sound] ?? [30])
  }

  glowing.value = d.sound
  if (glowTimer) clearTimeout(glowTimer)
  glowTimer = setTimeout(() => {
    glowing.value = null
  }, GLOW_MS)

  const meta = SOUNDS.find((s) => s.id === d.sound)
  capsule.value = {
    name: d.player_name ?? '',
    emoji: meta?.emoji ?? '🔊',
    label: meta?.label ?? d.sound,
    hue: getPlayerHue(d.player_id ?? d.player_name ?? ''),
  }
  if (capsuleTimer) clearTimeout(capsuleTimer)
  capsuleTimer = setTimeout(() => {
    capsule.value = null
  }, CAPSULE_MS)
}

onMounted(() => on('soundboard_played', onSoundboardPlayed))
onUnmounted(() => {
  off('soundboard_played', onSoundboardPlayed)
  if (glowTimer) clearTimeout(glowTimer)
  if (capsuleTimer) clearTimeout(capsuleTimer)
})
</script>

<style scoped>
.soundboard {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  justify-content: center;
  align-items: center;
}

/* Per UX spec: bounce + fading primary glow, no white flash. */
.sound-btn-glow {
  animation:
    btn-bounce 0.3s var(--ease-bounce),
    sound-glow 0.8s ease-out;
}

/* Recharge treatment on the pressed chip only — reads as "reloading",
   never as a dead board. */
.sound-btn-recharging {
  filter: saturate(0.4);
  transform: scale(0.94);
  transition:
    filter 1.2s linear,
    transform 1.2s var(--ease-smooth);
  cursor: default;
}

/* === Attributed event capsule === */
.event-capsule {
  position: fixed;
  /* Clear of the sticky header (~90px worst case with a two-line title) —
     right at the header's edge it read as clipped. */
  top: calc(var(--space-xl) * 3.5);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-md);
  border-radius: var(--radius-full);
  background: rgba(var(--color-surface-rgb), 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid hsl(var(--hue, 200) 80% 60% / 0.6);
  box-shadow: 0 0 16px hsl(var(--hue, 200) 80% 60% / 0.35);
  opacity: 0;
  pointer-events: none;
  /* Above the sticky glass header (z-index 10) — below it, the capsule
     drowns behind the header's near-opaque blurred background. */
  z-index: 20;
  transition: opacity 0.2s var(--ease-smooth);
}

.event-capsule--visible {
  opacity: 1;
  /* Own keyframes: award-pop would override the translateX(-50%) centering
     for the duration of the animation. */
  animation: capsule-pop 0.4s var(--ease-bounce);
}

@keyframes capsule-pop {
  0% {
    transform: translateX(-50%) scale(0.5) rotate(-4deg);
  }
  70% {
    transform: translateX(-50%) scale(1.08);
  }
  100% {
    transform: translateX(-50%) scale(1);
  }
}

.capsule-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: hsl(var(--hue, 200) 80% 60%);
  flex-shrink: 0;
}

.capsule-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: hsl(var(--hue, 200) 80% 75%);
}

.capsule-emoji {
  font-size: var(--text-xl);
  line-height: 1;
}

.capsule-label {
  font-size: var(--text-sm);
  color: var(--color-text);
}

/* Roomier capsule on wide screens — at 36px tall it vanishes on a 27". */
@media (min-width: 900px) {
  .event-capsule {
    padding: var(--space-sm) var(--space-lg);
  }
  .capsule-emoji {
    font-size: var(--text-2xl);
  }
  .capsule-name,
  .capsule-label {
    font-size: var(--text-base);
  }
}

@media (prefers-reduced-motion: reduce) {
  .sound-btn-glow {
    /* Adaptive, not subtractive: hold a static primary border instead of
       animating — the information survives without the motion. */
    animation: none;
    box-shadow: 0 0 0 2px var(--color-primary);
  }
  .event-capsule--visible {
    animation: none;
  }
  .sound-btn-recharging {
    transition: none;
    transform: none;
  }
}
</style>
