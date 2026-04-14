<template>
  <section v-if="state" class="blindtest-round">
    <div class="zone-info">
      <span class="text-display phase">{{ phaseLabel }}</span>
      <span class="round-info"> Manche {{ currentRound + 1 }} / {{ totalRounds }} </span>
    </div>

    <div class="zone-content">
      <audio
        v-if="audioActive"
        ref="audioRef"
        class="audio-el"
        :src="trackUrl"
        autoplay
        preload="auto"
      ></audio>

      <template v-if="phase === 'countdown'">
        <p class="hint">Prépare-toi...</p>
        <Countdown :from="3" @done="onCountdownDone" />
      </template>

      <div v-else-if="isAnswerPhase" class="answer-stage">
        <div
          v-if="phase === 'playing' && !locallyFound"
          class="mystery-orb"
          aria-hidden="true"
        ></div>
        <div v-else-if="showReveal" class="reveal anim-reveal-slide">
          <img v-if="revealCoverUrl" class="reveal-cover" :src="revealCoverUrl" alt="" />
          <h2 class="reveal-title text-display">{{ revealTitle }}</h2>
          <p class="reveal-artist">{{ revealArtist }}</p>
        </div>
        <p v-if="phase === 'playing' && !locallyFound" class="hint">Tape ce que tu entends</p>
        <AnswerInput
          ref="answerRef"
          :disabled="phase === 'playing_reveal' || locallyFound"
          @submit="onAnswer"
        />
        <div class="scoreboard-compact">
          <ScoreBoard :scores="totalScores" :players="playerMap" />
        </div>
      </div>

      <div v-else-if="phase === 'round_pause'" class="pause-stage">
        <div class="pause-indicator" aria-hidden="true"></div>
      </div>

      <template v-else-if="phase === 'finished'">
        <h2 class="finished-title text-display text-gradient">Terminé !</h2>
        <ScoreBoard :scores="totalScores" :players="playerMap" />
      </template>
    </div>

    <div class="zone-actions">
      <button
        v-if="phase === 'finished' && isHost"
        type="button"
        class="btn btn-primary"
        data-test="back-lobby"
        @click="onBackToLobby"
      >
        Retour au lobby
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import AnswerInput from './AnswerInput.vue'
import Countdown from './Countdown.vue'
import ScoreBoard from './ScoreBoard.vue'
import { useSocket } from '../composables/useSocket'
import { useVolume } from '../composables/useVolume'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import type { FuzzyResult } from '../types'

const router = useRouter()
const { emit: socketEmit, on: socketOn, off: socketOff } = useSocket()
const { attachMusic } = useVolume()
const auth = useAuthStore()
const roomStore = useRoomStore()
const gameStore = useGameStore()

const answerRef = ref<InstanceType<typeof AnswerInput> | null>(null)
const audioRef = ref<HTMLAudioElement | null>(null)
const locallyFound = ref(false)
const localAnswer = ref<{
  correct_title: string
  correct_artist: string
  cover_url: string
} | null>(null)
let detachMusic: (() => void) | null = null

watchEffect(() => {
  if (audioRef.value && !detachMusic) {
    detachMusic = attachMusic(audioRef.value)
  } else if (!audioRef.value && detachMusic) {
    detachMusic()
    detachMusic = null
  }
})

const state = computed(() => gameStore.state)
const phase = computed<string>(() => gameStore.state?.phase ?? '')
const currentRound = computed<number>(() => gameStore.state?.current_round ?? 0)
const totalRounds = computed<number>(() => gameStore.state?.total_rounds ?? 0)
const totalScores = computed<Record<string, number>>(() => gameStore.state?.total_scores ?? {})

const trackUrl = computed<string>(() => gameStore.state?.track?.preview_url ?? '')

const roundResults = computed(() => gameStore.state?.round_results)

const showReveal = computed(() => phase.value === 'playing_reveal' || locallyFound.value)
const revealCoverUrl = computed(() =>
  locallyFound.value ? (localAnswer.value?.cover_url ?? '') : (roundResults.value?.cover_url ?? ''),
)
const revealTitle = computed(() =>
  locallyFound.value
    ? (localAnswer.value?.correct_title ?? '')
    : (roundResults.value?.correct_title ?? ''),
)
const revealArtist = computed(() =>
  locallyFound.value
    ? (localAnswer.value?.correct_artist ?? '')
    : (roundResults.value?.correct_artist ?? ''),
)

const isAnswerPhase = computed(() => phase.value === 'playing' || phase.value === 'playing_reveal')

const audioActive = computed(() => !!trackUrl.value && isAnswerPhase.value)

const playerMap = computed<Record<string, { name: string }>>(() => {
  const players = roomStore.room?.players ?? []
  const map: Record<string, { name: string }> = {}
  for (const p of players) {
    map[p.id] = { name: p.name }
  }
  return map
})

const isHost = computed(() => roomStore.isHost)

const phaseLabel = computed(() => {
  const map: Record<string, string> = {
    countdown: 'Prêt ?',
    playing: 'À toi de jouer',
    playing_reveal: 'Révélation',
    round_pause: '...',
    finished: 'Terminé',
  }
  return map[phase.value] ?? phase.value
})

let playStart = 0

watch(
  phase,
  (newPhase, oldPhase) => {
    if (newPhase === 'playing') playStart = Date.now()
    if (newPhase === 'playing' && oldPhase !== 'playing') {
      locallyFound.value = false
      localAnswer.value = null
    }
    if (newPhase === 'round_pause' && oldPhase === 'playing_reveal' && audioRef.value) {
      audioRef.value.pause()
    }
  },
  { immediate: true },
)

const roomCode = computed(() => roomStore.room?.code ?? '')

function onCountdownDone() {
  socketEmit('game_event', {
    code: roomCode.value,
    event_type: 'countdown_done',
    payload: {},
  })
}

function onAnswer(text: string) {
  socketEmit('game_event', {
    code: roomCode.value,
    event_type: 'answer',
    payload: { text, time_ms: Date.now() - playStart },
  })
}

function onBackToLobby() {
  void router.push(`/${roomCode.value}`)
}

function onEventResult(data: unknown) {
  const d = data as FuzzyResult & {
    player_id?: string
    correct_title?: string
    correct_artist?: string
    cover_url?: string
  }
  if (d.player_id !== auth.userId) return
  answerRef.value?.setResult({
    title_match: d.title_match,
    artist_match: d.artist_match,
    bonus: d.bonus,
    distance: d.distance,
  })
  if (d.bonus && d.correct_title && d.correct_artist) {
    locallyFound.value = true
    localAnswer.value = {
      correct_title: d.correct_title,
      correct_artist: d.correct_artist,
      cover_url: d.cover_url ?? '',
    }
  }
}

onMounted(() => {
  socketOn('game_event_result', onEventResult)
})

onBeforeUnmount(() => {
  socketOff('game_event_result', onEventResult)
  detachMusic?.()
  detachMusic = null
})
</script>

<style scoped>
.blindtest-round {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  width: 100%;
}

.zone-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  align-items: center;
  padding: var(--space-md);
  background: linear-gradient(
    180deg,
    rgba(var(--color-bg-rgb), 0.95),
    rgba(var(--color-bg-rgb), 0.7)
  );
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
}

.phase {
  font-size: var(--text-xl);
  color: var(--color-accent);
  letter-spacing: 2px;
  text-shadow: 0 0 15px rgba(var(--color-accent-rgb), 0.4);
}

.round-info {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  letter-spacing: 1px;
}

.zone-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-lg);
  padding: var(--space-lg) var(--space-md);
  min-height: 60vh;
}

.answer-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
  width: 100%;
}

.hint {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.mystery-orb {
  position: relative;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background:
    radial-gradient(
      circle at 35% 35%,
      rgba(var(--color-primary-rgb), 0.55),
      rgba(var(--color-secondary-rgb), 0.35) 45%,
      rgba(var(--color-accent-rgb), 0.15) 75%,
      transparent 100%
    ),
    conic-gradient(
      from 0deg,
      var(--color-primary),
      var(--color-secondary),
      var(--color-accent),
      var(--color-primary)
    );
  filter: blur(2px);
  box-shadow:
    0 0 60px rgba(var(--color-primary-rgb), 0.45),
    0 0 120px rgba(var(--color-accent-rgb), 0.25);
  animation: cover-spin 8s linear infinite;
}

.audio-el {
  display: none;
}

.scoreboard-compact {
  width: 100%;
  max-width: 420px;
  opacity: 0.7;
  font-size: var(--text-sm);
  transform: scale(0.92);
  transform-origin: top center;
  margin-top: var(--space-xs);
}

.scoreboard-compact :deep(.score-row) {
  padding: 0.3rem 0.65rem;
  font-size: var(--text-sm);
}

.reveal {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-lg);
  background: linear-gradient(
    135deg,
    rgba(var(--color-primary-rgb), 0.12),
    rgba(var(--color-accent-rgb), 0.08)
  );
  border: 1px solid rgba(var(--color-primary-rgb), 0.25);
  border-radius: var(--radius-lg);
  box-shadow: 0 0 40px rgba(var(--color-primary-rgb), 0.2);
  width: 100%;
  max-width: 420px;
}

.reveal-cover {
  width: 120px;
  height: 120px;
  border-radius: var(--radius-md);
  object-fit: cover;
}

.reveal-title {
  font-size: var(--text-2xl);
  color: var(--color-text);
  text-align: center;
  text-shadow: 0 0 20px rgba(var(--color-accent-rgb), 0.5);
}

.reveal-artist {
  color: var(--color-text-muted);
  font-size: var(--text-lg);
  letter-spacing: 1px;
}

.pause-stage {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
}

.pause-indicator {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(var(--color-accent-rgb), 0.3),
    rgba(var(--color-primary-rgb), 0.1) 60%,
    transparent 100%
  );
  box-shadow: 0 0 40px rgba(var(--color-accent-rgb), 0.35);
  animation: pulse-breath 1.2s ease-in-out infinite;
}

.finished-title {
  font-size: var(--text-hero);
  text-align: center;
}

.zone-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: center;
  padding: var(--space-md);
  padding-bottom: calc(var(--space-md) + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, transparent, rgba(var(--color-bg-rgb), 0.92));
}

.zone-actions .btn {
  min-height: 48px;
  min-width: 180px;
}

@keyframes cover-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse-breath {
  0%,
  100% {
    transform: scale(0.9);
    opacity: 0.6;
  }
  50% {
    transform: scale(1.1);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cover-halo::before {
    animation: none;
  }
  .pause-indicator {
    animation: none;
  }
}

@media (min-width: 768px) {
  .blindtest-round {
    max-width: 640px;
    margin: 0 auto;
  }
  .mystery-orb {
    width: 220px;
    height: 220px;
  }
}
</style>
