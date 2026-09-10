<template>
  <div class="reaction-bar" role="toolbar" aria-label="Réactions emoji">
    <button
      v-for="r in REACTIONS"
      :key="r"
      type="button"
      class="react-btn"
      :data-test="`react-${r}`"
      :aria-label="`Réagir ${r}`"
      @click="send(r)"
    >
      {{ r }}
    </button>
  </div>
  <div class="floating-reactions" aria-hidden="true">
    <span
      v-for="fr in floating"
      :key="fr.id"
      class="floating"
      :style="{ left: `${fr.x}%`, '--drift': `${fr.drift}px`, '--hue': String(fr.hue) }"
    >
      <span class="floating-emoji">{{ fr.emoji }}</span>
      <span class="floating-name"><span class="floating-dot"></span>{{ fr.name }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useSocket } from '../composables/useSocket'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { getPlayerHue } from '../lib/playerHue'
import { randomUnit } from '../lib/random'

const REACTIONS = ['😂', '👏', '💀', '🔥', '😱', '❤️'] as const

// Matches the float-up animation length — the DOM node outlives the fade by
// a hair so the animation never gets cut.
const FLOAT_MS = 1600
// Six bored players spamming must feel like a crowd, not wallpaper the
// screen: oldest floats get culled beyond this.
const MAX_FLOATS = 12

const { emit, on, off } = useSocket()
const roomStore = useRoomStore()
const gameStore = useGameStore()

interface FloatingReaction {
  id: number
  emoji: string
  name: string
  x: number
  drift: number
  hue: number
}

const floating = ref<FloatingReaction[]>([])
let idCounter = 0

function send(emoji: string): void {
  const code = roomStore.room?.code
  if (!code) return
  // Strict payload: the server rejects any extra key (extra="forbid") and
  // stamps player identity from its own session.
  emit('reaction', { code, emoji })
}

function spawnX(): number {
  // Only picks where a decorative emoji drifts on screen; identity and
  // ordering come from the server, never from here. While players are
  // heads-down answering, floats stay in the side gutters so they
  // geometrically cannot cross the input, waveform or countdown.
  if (gameStore.state?.phase === 'playing') {
    const gutterOffset = 4 + randomUnit() * 12
    return randomUnit() < 0.5 ? gutterOffset : 96 - gutterOffset + 4
  }
  return 10 + randomUnit() * 80
}

function onReactionReceived(data: unknown): void {
  const d = data as { player_id?: string; player_name?: string; emoji?: string }
  if (!d?.emoji) return
  const id = idCounter++
  floating.value.push({
    id,
    emoji: d.emoji,
    name: d.player_name ?? '',
    x: spawnX(),
    drift: (randomUnit() - 0.5) * 20,
    hue: getPlayerHue(d.player_id ?? d.player_name ?? ''),
  })
  if (floating.value.length > MAX_FLOATS) {
    floating.value = floating.value.slice(-MAX_FLOATS)
  }
  setTimeout(() => {
    floating.value = floating.value.filter((f) => f.id !== id)
  }, FLOAT_MS)
}

onMounted(() => on('reaction_received', onReactionReceived))
onUnmounted(() => off('reaction_received', onReactionReceived))
</script>

<style scoped>
.reaction-bar {
  display: flex;
  gap: var(--space-sm);
  justify-content: center;
  flex-wrap: wrap;
}

.react-btn:active {
  animation: btn-bounce 0.3s var(--ease-bounce);
}

.floating-reactions {
  position: fixed;
  inset: 0;
  pointer-events: none;
  /* Below the glass header (z-index 10): floats slide behind the blur and
     read as depth instead of noise. */
  z-index: 8;
}

.floating {
  position: absolute;
  bottom: 18%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  animation: float-up 1.5s ease-out forwards;
  transform: translateX(var(--drift, 0));
}

.floating-emoji {
  font-size: var(--text-2xl);
}

.floating-name {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: var(--text-xs);
  color: hsl(var(--hue, 200) 80% 75%);
  text-shadow: 0 1px 4px rgba(var(--color-bg-rgb), 0.8);
}

.floating-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: hsl(var(--hue, 200) 80% 60%);
}

@keyframes float-fade {
  0% {
    opacity: 0;
  }
  15%,
  70% {
    opacity: 0.9;
  }
  100% {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .floating {
    /* Adaptive: same information, opacity only — no travel. */
    animation: float-fade 1.5s ease-out forwards;
  }
  .react-btn:active {
    animation: none;
  }
}
</style>
