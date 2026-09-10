<template>
  <ol class="podium" role="list" aria-label="Top 3 du round">
    <li
      v-for="slot in slots"
      :key="slot.rank"
      class="podium-slot"
      :class="[`rank-${slot.rank}`, { placeholder: !slot.winner }]"
      :style="slotStyle(slot)"
      :aria-label="slotLabel(slot)"
    >
      <span class="emoji" aria-hidden="true">{{ slot.emoji }}</span>
      <span class="name">{{ slot.winner ? slot.winner.name : '—' }}</span>
      <span class="time">{{ slot.winner ? formatTime(slot.winner.time_ms) : '—' }}</span>
    </li>
  </ol>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Winner } from '../types'
import { getPlayerHue } from '../lib/playerHue'
import { formatTime } from '../lib/time'

const props = defineProps<{
  winners: Winner[]
}>()

type PodiumRank = 1 | 2 | 3

interface PodiumSlot {
  rank: PodiumRank
  order: number
  emoji: string
  delayMs: number
  winner: Winner | null
}

function slotMeta(rank: PodiumRank): { emoji: string; delayMs: number; order: number } {
  if (rank === 1) return { emoji: '🥇', delayMs: 0, order: 2 }
  if (rank === 2) return { emoji: '🥈', delayMs: 120, order: 1 }
  return { emoji: '🥉', delayMs: 240, order: 3 }
}

const slots = computed<PodiumSlot[]>(() => {
  const ranks: PodiumRank[] = [1, 2, 3]
  return ranks
    .map((rank) => {
      const meta = slotMeta(rank)
      const winner = props.winners[rank - 1] ?? null
      return { rank, order: meta.order, emoji: meta.emoji, delayMs: meta.delayMs, winner }
    })
    .sort((a, b) => a.order - b.order)
})

function slotStyle(slot: PodiumSlot): Record<string, string> {
  const hue = slot.winner ? getPlayerHue(slot.winner.player_id) : 0
  return {
    '--hue': String(hue),
    '--delay': `${slot.delayMs}ms`,
    animationDelay: `${slot.delayMs}ms`,
  }
}

function slotLabel(slot: PodiumSlot): string {
  if (!slot.winner) {
    return `Rang ${slot.rank} : vide`
  }
  return `Rang ${slot.rank} : ${slot.winner.name} en ${formatTime(slot.winner.time_ms)}`
}
</script>

<style scoped>
.podium {
  list-style: none;
  padding: 0;
  margin: var(--space-md) 0 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm);
  width: 100%;
  max-width: 420px;
  align-items: end;
}

.podium-slot {
  --hue: 200;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-md) var(--space-sm);
  border-radius: var(--radius-md);
  background: linear-gradient(
    180deg,
    hsla(var(--hue), 80%, 55%, 0.28),
    rgba(var(--color-surface-rgb), 0.9)
  );
  border: 1px solid hsla(var(--hue), 90%, 60%, 0.4);
  box-shadow:
    0 0 14px hsla(var(--hue), 90%, 60%, 0.35),
    0 4px 20px rgba(var(--color-black-rgb), 0.35);
  opacity: 0;
  animation: reveal-slide 0.5s var(--ease-bounce) forwards;
}

.podium-slot.placeholder {
  background: linear-gradient(
    180deg,
    rgba(var(--color-white-rgb), 0.04),
    rgba(var(--color-surface-rgb), 0.75)
  );
  border-color: rgba(var(--color-white-rgb), 0.08);
  box-shadow: none;
  color: var(--color-text-muted);
}

.podium-slot.rank-1 {
  min-height: 140px;
}
.podium-slot.rank-2 {
  min-height: 110px;
}
.podium-slot.rank-3 {
  min-height: 92px;
}

.emoji {
  font-size: var(--text-2xl);
  line-height: 1;
}

.name {
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-base);
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.placeholder .name,
.placeholder .time {
  color: var(--color-text-muted);
}

.time {
  font-family: var(--font-display);
  color: var(--color-warning);
  font-size: var(--text-sm);
  letter-spacing: 1px;
  text-shadow: 0 0 10px rgba(var(--color-warning-rgb), 0.45);
}

@media (prefers-reduced-motion: reduce) {
  .podium-slot {
    animation: none;
    opacity: 1;
  }
}
</style>
