<template>
  <ol class="player-list">
    <li
      v-for="(player, idx) in players"
      :key="player.id"
      class="player-row"
      :class="{
        'is-me': player.id === currentUserId,
        'is-host': player.is_host,
      }"
      :style="{ '--hue': getPlayerHue(player.id) }"
    >
      <span class="player-rank" aria-hidden="true">
        {{ String(idx + 1).padStart(2, '0') }}
      </span>

      <div class="player-avatar" aria-hidden="true">
        {{ player.name[0]?.toUpperCase() }}
      </div>

      <div class="player-main">
        <span class="player-name">{{ player.name }}</span>
        <div class="player-meta">
          <span v-if="player.is_host" class="tag tag-host">★ HOST</span>
          <span v-else-if="player.id === currentUserId" class="tag tag-me">TOI</span>
          <span v-else class="tag tag-guest">GUEST</span>
          <span class="ping-wave" aria-hidden="true">
            <span class="ping-bar"></span>
            <span class="ping-bar"></span>
            <span class="ping-bar"></span>
          </span>
        </div>
      </div>

      <button
        v-if="canKick && !player.is_host"
        class="btn-kick"
        :aria-label="`Exclure ${player.name}`"
        @click="emit('kick', player.id)"
      >
        ✕
      </button>
    </li>
  </ol>
</template>

<script setup lang="ts">
import type { Player } from '../types'
import { useAuthStore } from '../stores/auth'

withDefaults(
  defineProps<{
    players: Player[]
    canKick?: boolean
  }>(),
  { canKick: false },
)

const emit = defineEmits<{
  kick: [playerId: string]
}>()

const auth = useAuthStore()
const currentUserId = auth.userId

/**
 * Stable hash → hue: every player gets their own neon color based on their
 * user id, so the roster looks like a real club guest list, not a flat list.
 */
function getPlayerHue(id: string): number {
  let h = 5381
  for (const ch of id) {
    // codePointAt(0) handles surrogate pairs correctly, unlike charCodeAt.
    h = ((h << 5) + h + (ch.codePointAt(0) ?? 0)) >>> 0
  }
  return h % 360
}
</script>

<style scoped>
.player-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.player-row {
  --hue: 200;
  position: relative;
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: 0.85rem;
  padding: 0.65rem 0.9rem 0.65rem 1.1rem;
  background: linear-gradient(
    90deg,
    hsla(var(--hue), 60%, 40%, 0.12) 0%,
    rgba(var(--color-bg-rgb), 0.45) 60%
  );
  border: 1px solid rgba(var(--color-white-rgb), 0.07);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition:
    transform 0.18s var(--ease-smooth),
    border-color 0.2s,
    box-shadow 0.2s;
  animation: player-enter 0.55s var(--ease-bounce) both;
}

/* Neon left stripe — the "VIP wristband" */
.player-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: hsl(var(--hue), 95%, 62%);
  box-shadow:
    0 0 12px hsl(var(--hue), 95%, 62%),
    0 0 24px hsla(var(--hue), 95%, 62%, 0.5);
}

.player-row:hover {
  border-color: hsla(var(--hue), 90%, 60%, 0.4);
  transform: translateX(2px);
  box-shadow: 0 4px 18px hsla(var(--hue), 90%, 40%, 0.2);
}

.player-row.is-me {
  background: linear-gradient(
    90deg,
    rgba(var(--color-primary-rgb), 0.16) 0%,
    rgba(var(--color-bg-rgb), 0.5) 70%
  );
  border-color: rgba(var(--color-primary-rgb), 0.32);
}
.player-row.is-me::before {
  background: var(--color-primary);
  box-shadow:
    0 0 12px var(--color-primary),
    0 0 24px rgba(var(--color-primary-rgb), 0.5);
}

.player-row.is-host {
  background: linear-gradient(
    90deg,
    rgba(var(--color-warning-rgb), 0.14) 0%,
    rgba(var(--color-primary-rgb), 0.08) 50%,
    rgba(var(--color-bg-rgb), 0.45) 100%
  );
  border-color: rgba(var(--color-warning-rgb), 0.28);
}
.player-row.is-host::before {
  background: linear-gradient(180deg, var(--color-warning), var(--color-primary));
  box-shadow:
    0 0 14px rgba(var(--color-warning-rgb), 0.7),
    0 0 28px rgba(var(--color-primary-rgb), 0.4);
}

/* Rank number — terminal display style */
.player-rank {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  letter-spacing: 2px;
  min-width: 22px;
  opacity: 0.55;
  text-align: center;
}

.player-avatar {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--color-text);
  background: linear-gradient(
    135deg,
    hsl(var(--hue), 95%, 60%) 0%,
    hsl(calc(var(--hue) + 40), 85%, 45%) 100%
  );
  border-radius: 50%;
  box-shadow:
    0 0 0 1px rgba(var(--color-white-rgb), 0.12),
    0 0 20px hsla(var(--hue), 95%, 55%, 0.45),
    inset 0 0 0 1px rgba(var(--color-white-rgb), 0.15);
  text-transform: uppercase;
  flex-shrink: 0;
  text-shadow: 0 1px 2px rgba(var(--color-black-rgb), 0.3);
}
.is-host .player-avatar {
  background: linear-gradient(135deg, var(--color-warning) 0%, var(--color-primary) 100%);
  box-shadow:
    0 0 0 2px rgba(var(--color-warning-rgb), 0.4),
    0 0 22px rgba(var(--color-warning-rgb), 0.5),
    0 0 40px rgba(var(--color-primary-rgb), 0.3);
}

.player-main {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}
.player-name {
  font-family: var(--font-body);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}
.is-me .player-name {
  color: var(--color-text);
}

.player-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.15rem;
}

.tag {
  font-family: var(--font-display);
  font-size: 0.62rem;
  padding: 0.12rem 0.5rem;
  border-radius: var(--radius-full);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 700;
  white-space: nowrap;
}
.tag-host {
  background: linear-gradient(
    135deg,
    rgba(var(--color-warning-rgb), 0.22),
    rgba(var(--color-primary-rgb), 0.15)
  );
  color: var(--color-warning);
  border: 1px solid rgba(var(--color-warning-rgb), 0.4);
  box-shadow: 0 0 14px rgba(var(--color-warning-rgb), 0.25);
}
.tag-me {
  background: rgba(var(--color-primary-rgb), 0.18);
  color: var(--color-primary);
  border: 1px solid rgba(var(--color-primary-rgb), 0.4);
}
.tag-guest {
  background: hsla(var(--hue), 80%, 50%, 0.12);
  color: hsl(var(--hue), 90%, 75%);
  border: 1px solid hsla(var(--hue), 80%, 60%, 0.35);
}

/* Tiny animated equalizer = "connected / alive" indicator */
.ping-wave {
  display: inline-flex;
  align-items: flex-end;
  gap: 1.5px;
  height: 10px;
  opacity: 0.6;
}
.ping-bar {
  width: 2px;
  background: hsl(var(--hue), 90%, 65%);
  border-radius: 1px;
  animation: ping-wave 1.4s ease-in-out infinite;
}
.ping-bar:nth-child(1) {
  animation-delay: 0s;
  height: 35%;
}
.ping-bar:nth-child(2) {
  animation-delay: 0.18s;
  height: 65%;
}
.ping-bar:nth-child(3) {
  animation-delay: 0.36s;
  height: 45%;
}

.btn-kick {
  background: none;
  border: 1px solid rgba(var(--color-error-rgb), 0.3);
  color: rgba(var(--color-error-rgb), 0.75);
  border-radius: var(--radius-sm);
  width: 28px;
  height: 28px;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s,
    transform 0.15s;
}
.btn-kick:hover {
  background: rgba(var(--color-error-rgb), 0.18);
  color: var(--color-error);
  border-color: var(--color-error);
  transform: scale(1.08);
}

@keyframes player-enter {
  0% {
    opacity: 0;
    transform: translateX(-16px);
    filter: blur(4px);
  }
  100% {
    opacity: 1;
    transform: translateX(0);
    filter: blur(0);
  }
}
@keyframes ping-wave {
  0%,
  100% {
    transform: scaleY(0.6);
    opacity: 0.5;
  }
  50% {
    transform: scaleY(1.2);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .player-row,
  .ping-bar {
    animation: none !important;
  }
}

/* Touch-friendly on small screens */
@media (max-width: 560px) {
  .player-row {
    gap: 0.7rem;
    padding: 0.6rem 0.75rem 0.6rem 1rem;
  }
  .player-avatar {
    width: 34px;
    height: 34px;
  }
  .btn-kick {
    width: 34px;
    height: 34px;
    font-size: 1rem;
  }
}
</style>
