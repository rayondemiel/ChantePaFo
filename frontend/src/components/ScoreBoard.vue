<template>
  <ol class="scoreboard">
    <li
      v-for="(entry, idx) in ranked"
      :key="entry.id"
      class="score-row"
      :class="{ 'score-row-leader': idx === 0 && ranked.length > 1 }"
      :style="{ '--hue': getPlayerHue(entry.id) }"
    >
      <span class="score-rank"
        ><span v-if="idx === 0 && ranked.length > 1" class="crown" aria-hidden="true"
          >&#128081;</span
        >{{ idx + 1 }}</span
      >
      <span class="score-name">{{ entry.name }}</span>
      <span class="score-pts">{{ entry.score }}</span>
    </li>
  </ol>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getPlayerHue } from '../lib/playerHue'

const props = defineProps<{
  scores: Record<string, number>
  players: Record<string, { name: string }>
}>()

const ranked = computed(() => {
  return Object.entries(props.scores)
    .map(([id, score]) => ({
      id,
      score,
      // eslint-disable-next-line security/detect-object-injection
      name: props.players[id]?.name ?? id,
    }))
    .sort((a, b) => b.score - a.score)
})
</script>

<style scoped>
.scoreboard {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
}

.score-row {
  --hue: 200;
  position: relative;
  font-size: var(--text-base);
  padding: 0.55rem 0.9rem;
  background: linear-gradient(
    90deg,
    hsla(var(--hue), 70%, 45%, 0.14) 0%,
    rgba(var(--color-surface-rgb), 0.9) 70%
  );
  border: 1px solid rgba(var(--color-white-rgb), 0.06);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition:
    transform 0.18s var(--ease-smooth),
    box-shadow 0.3s var(--ease-smooth),
    background 0.3s var(--ease-smooth);
}

.score-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: hsl(var(--hue), 95%, 62%);
  box-shadow:
    0 0 10px hsl(var(--hue), 95%, 62%),
    0 0 20px hsla(var(--hue), 95%, 62%, 0.45);
}

.score-row:hover {
  transform: translateX(2px);
  box-shadow: 0 0 12px hsla(var(--hue), 90%, 60%, 0.25);
}

/* First place: golden glow */
.score-row:first-child {
  background: linear-gradient(
    90deg,
    rgba(var(--color-warning-rgb), 0.22) 0%,
    rgba(var(--color-primary-rgb), 0.1) 55%,
    rgba(var(--color-surface-rgb), 0.85) 100%
  );
  border-color: rgba(var(--color-warning-rgb), 0.3);
  box-shadow: 0 0 18px rgba(var(--color-warning-rgb), 0.18);
}

/* Leader with golden glow border */
.score-row-leader {
  border-color: rgba(var(--color-warning-rgb), 0.45);
  box-shadow:
    0 0 18px rgba(var(--color-warning-rgb), 0.2),
    inset 0 0 20px rgba(var(--color-warning-rgb), 0.05);
  animation: leader-pulse 2s ease-in-out infinite;
}

.crown {
  font-size: 0.8em;
  margin-right: 0.15em;
  filter: drop-shadow(0 0 4px rgba(var(--color-warning-rgb), 0.6));
  animation: crown-float 2s ease-in-out infinite;
}

.score-rank {
  font-family: var(--font-display);
  color: var(--color-text-muted);
  min-width: 22px;
  letter-spacing: 1px;
  display: inline-flex;
  align-items: center;
}

.score-row:first-child .score-rank {
  color: var(--color-warning);
  text-shadow: 0 0 10px rgba(var(--color-warning-rgb), 0.5);
}

.score-name {
  flex: 1;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.score-pts {
  font-family: var(--font-display);
  color: var(--color-warning);
  letter-spacing: 1px;
  text-shadow:
    0 0 8px rgba(var(--color-warning-rgb), 0.3),
    0 0 16px rgba(var(--color-warning-rgb), 0.15);
}

@keyframes leader-pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.01);
  }
}

@keyframes crown-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-1px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .score-row-leader {
    animation: none;
  }
  .crown {
    animation: none;
  }
}
</style>
