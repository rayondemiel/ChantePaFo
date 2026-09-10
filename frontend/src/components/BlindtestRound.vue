<template>
  <section
    v-if="state"
    class="blindtest-round"
    :class="{
      'layout-desktop': !isMobile && phase !== 'finished',
      'layout-mobile': isMobile,
      'layout-finished': phase === 'finished',
    }"
  >
    <div class="game-body">
      <div
        class="zone-content"
        :class="{ 'stress-pulse': phase === 'playing' && stressLevel === 'critical' }"
      >
        <audio
          v-if="audioActive"
          ref="audioRef"
          class="audio-el"
          crossorigin="anonymous"
          :src="trackUrl"
          autoplay
          preload="auto"
          @error="onAudioError"
        ></audio>

        <Transition name="phase" mode="out-in">
          <div v-if="phase === 'countdown'" key="countdown" class="countdown-stage">
            <p class="hint">Prépare-toi...</p>
            <Countdown :from="3" @done="onCountdownDone" />
          </div>
        </Transition>

        <Transition name="phase" mode="out-in">
          <div v-if="isAnswerPhase" :key="'answer-' + phase" class="answer-stage">
            <!-- Hero cluster: the countdown anchors to the orb/reveal, not to
                 the stage — the stage now stretches to fill the screen and an
                 absolute top-right there strands the timer far from the action. -->
            <div class="stage-hero">
              <div
                v-if="phase === 'playing' && !locallyFound"
                class="mystery-orb"
                aria-hidden="true"
              >
                <div class="synth-ring synth-ring-3"></div>
                <div class="synth-ring synth-ring-2"></div>
                <div class="synth-ring synth-ring-1"></div>
                <div class="synth-sun">
                  <span class="orb-symbol">&#9835;</span>
                </div>
                <div class="synth-sonar"></div>
              </div>
              <div v-else-if="showReveal" class="reveal anim-reveal-slide">
                <img v-if="revealCoverUrl" class="reveal-cover" :src="revealCoverUrl" alt="" />
                <h2 class="reveal-title text-display">{{ revealTitle }}</h2>
                <p class="reveal-artist">{{ revealArtist }}</p>
              </div>
            </div>
            <CircularCountdown
              v-if="phase === 'playing'"
              class="playing-countdown"
              :duration="playingDuration"
              :elapsed="roundElapsedAtStart"
              :running="phase === 'playing'"
            />
            <TrackWaveform
              :progress="waveformProgress"
              :frozen="phase === 'playing_reveal'"
              :markers="phase === 'playing_reveal' ? waveformMarkers : []"
              :total-duration-ms="playingDuration * 1000"
              :stress-level="stressLevel"
            />
            <p v-if="phase === 'playing' && !locallyFound" class="hint">Tape ce que tu entends</p>
            <div
              v-if="locallyFound && phase === 'playing'"
              class="found-overlay"
              aria-live="polite"
            >
              <span class="found-check">&#10003;</span>
              <span class="found-label">Trouvé !</span>
            </div>
            <AnswerInput
              ref="answerRef"
              :disabled="phase === 'playing_reveal' || locallyFound"
              :class="{ 'answer-found': locallyFound }"
              @submit="onAnswer"
            />
            <!-- Live ticker for mobile (inline) -->
            <ul
              v-if="isMobile && phase === 'playing' && liveFound.length > 0"
              class="live-ticker"
              aria-label="Joueurs ayant trouvé"
            >
              <li
                v-for="entry in liveFound"
                :key="entry.player_id"
                class="ticker-pill anim-slide-right"
                :style="{
                  '--hue': getPlayerHue(entry.player_id),
                  '--match-bg': matchColor(entry.match_type),
                }"
              >
                <span class="ticker-avatar" aria-hidden="true"></span>
                <span class="ticker-name">{{ entry.name }}</span>
                <span class="ticker-match" :class="'match-' + entry.match_type">{{
                  matchLabel(entry.match_type)
                }}</span>
                <span class="ticker-time">{{ formatTime(entry.time_ms) }}</span>
                <span v-if="entry.points > 0" class="ticker-points">+{{ entry.points }}</span>
                <span
                  v-if="entry.match_type === 'bonus' && isFirstBonus(entry.player_id)"
                  class="ticker-badge"
                  >&#9889; 1er</span
                >
              </li>
            </ul>
            <RoundPodium v-if="phase === 'playing_reveal'" :winners="roundResults?.winners ?? []" />
            <!-- Compact scoreboard (desktop sidebar takes over, but wrapper persists) -->
            <div class="scoreboard-compact">
              <ScoreBoard v-if="isMobile" :scores="totalScores" :players="playerMap" />
            </div>
          </div>
        </Transition>

        <Transition name="phase" mode="out-in">
          <div v-if="phase === 'round_pause'" key="pause" class="pause-stage">
            <div class="pause-indicator" aria-hidden="true"></div>
            <p class="pause-label text-display">
              {{ isLastRound ? 'Résultats...' : 'Manche suivante...' }}
            </p>
            <!-- Mobile-only scoreboard during pause -->
            <div v-if="isMobile" class="pause-scoreboard">
              <ScoreBoard :scores="totalScores" :players="playerMap" />
            </div>
          </div>
        </Transition>

        <Transition name="phase" mode="out-in">
          <div v-if="phase === 'finished'" key="finished" class="finished-stage">
            <h2 class="finished-title text-display text-gradient">Bien joué à toutes et tous !</h2>

            <div class="finished-body" :class="{ 'finished-body--desktop': !isMobile }">
              <!-- Game Podium — top 3 overall scorers -->
              <div v-if="topThree.length > 0" class="game-podium" aria-label="Podium final">
                <template v-for="(slot, slotIdx) in podiumSlots" :key="slotIdx">
                  <div
                    v-if="slot"
                    class="podium-block"
                    :class="[`podium-rank-${slot.rank}`, { 'podium-champion': slot.rank === 1 }]"
                    :style="{
                      '--hue': slot.hue,
                      '--podium-delay': `${slot.rank === 2 ? 0 : slot.rank === 1 ? 0.3 : 0.6}s`,
                    }"
                  >
                    <span class="podium-medal" aria-hidden="true">{{
                      slot.rank === 1
                        ? '\uD83E\uDD47'
                        : slot.rank === 2
                          ? '\uD83E\uDD48'
                          : '\uD83E\uDD49'
                    }}</span>
                    <span v-if="slot.rank === 1" class="podium-crown" aria-hidden="true"
                      >&#128081;</span
                    >
                    <span
                      class="podium-name"
                      :class="{ 'podium-name-champion': slot.rank === 1 }"
                      >{{ slot.name }}</span
                    >
                    <span class="podium-score">{{ slot.score }} pts</span>
                    <div class="podium-bar" aria-hidden="true"></div>
                  </div>
                  <div
                    v-else
                    class="podium-block podium-empty"
                    :class="`podium-rank-${slotIdx === 0 ? 2 : slotIdx === 2 ? 3 : 1}`"
                  >
                    <span class="podium-medal" aria-hidden="true">{{
                      slotIdx === 0
                        ? '\uD83E\uDD48'
                        : slotIdx === 2
                          ? '\uD83E\uDD49'
                          : '\uD83E\uDD47'
                    }}</span>
                    <span class="podium-name">&mdash;</span>
                    <div class="podium-bar" aria-hidden="true"></div>
                  </div>
                </template>
              </div>

              <!-- Classement + host actions: sidebar on desktop (always in
                   view), right under the podium on mobile so the result is
                   the second thing a guest sees, not the last. -->
              <div class="finished-side">
                <div class="final-scoreboard">
                  <h3 class="final-scoreboard-heading text-display">Classement</h3>
                  <ScoreBoard
                    :scores="finalDisplayScores"
                    :players="playerMap"
                    class="scoreboard-final"
                  />
                </div>
                <FinishedActions
                  v-if="!isMobile"
                  :is-host="isHost"
                  @back="onBackToLobby"
                  @replay="onReplay"
                />
              </div>

              <div class="finished-main">
                <!-- Awards ceremony -->
                <div v-if="displayAwards.length > 0" class="awards-ceremony">
                  <h3 class="awards-heading text-display">Awards</h3>
                  <div class="awards-grid">
                    <div
                      v-for="(award, i) in displayAwards"
                      :key="award.id"
                      class="award-card"
                      :class="{ 'award-maestro': i === 0 }"
                      :style="{
                        '--hue': getPlayerHue(award.player_id),
                        'animation-delay': `${i * 0.8}s`,
                      }"
                    >
                      <span class="award-emoji">{{ award.emoji }}</span>
                      <div class="award-body">
                        <span class="award-title">{{ award.title }}</span>
                        <span class="award-player">{{ award.player_name }}</span>
                        <span class="award-detail">{{ award.detail }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Setlist — the story of the night, round by round -->
                <div v-if="setlist.length > 0" class="setlist-section">
                  <h3 class="setlist-heading text-display">Setlist</h3>
                  <p class="setlist-kicker">qui a dégainé en premier</p>
                  <ol class="setlist">
                    <li
                      v-for="(t, i) in setlist"
                      :key="t.round"
                      class="setlist-row"
                      :class="`setlist-row--${t.kind}`"
                      :style="{ 'animation-delay': `${1 + Math.min(i, 12) * 0.07}s` }"
                    >
                      <span class="setlist-round" aria-hidden="true">{{ t.round }}</span>
                      <img
                        v-if="t.cover_url"
                        class="setlist-cover"
                        :src="t.cover_url"
                        alt=""
                        loading="lazy"
                      />
                      <span v-else class="setlist-cover setlist-cover--fallback" aria-hidden="true"
                        >&#9835;</span
                      >
                      <span class="setlist-meta">
                        <span class="setlist-title" :title="t.title">{{ t.title }}</span>
                        <span class="setlist-artist" :title="t.artist">{{ t.artist }}</span>
                      </span>
                      <span class="setlist-chips">
                        <template v-if="t.kind === 'parfait'">
                          <span
                            class="setlist-chip chip-parfait"
                            :style="{ '--hue': t.titleHue }"
                            :title="t.first_title!.name"
                          >
                            <span class="chip-glyph" aria-hidden="true">★</span>
                            <span class="chip-dot" aria-hidden="true"></span>
                            <span class="chip-name">{{ t.first_title!.name }}</span>
                            <span class="chip-time"
                              ><template v-if="t.isFastestTitle">⚡</template
                              >{{ formatTime(t.parfaitMs) }}</span
                            >
                          </span>
                        </template>
                        <template v-else-if="t.kind === 'nobody'">
                          <span class="setlist-chip chip-ghost chip-nobody"
                            >Personne&nbsp;! 🦗</span
                          >
                        </template>
                        <template v-else>
                          <span
                            v-if="t.first_title"
                            class="setlist-chip chip-title"
                            :style="{ '--hue': t.titleHue }"
                            :title="t.first_title.name"
                          >
                            <span class="chip-glyph" aria-hidden="true">T</span>
                            <span class="chip-dot" aria-hidden="true"></span>
                            <span class="chip-name">{{ t.first_title.name }}</span>
                            <span class="chip-time"
                              ><template v-if="t.isFastestTitle">⚡</template
                              >{{ formatTime(t.first_title.time_ms) }}</span
                            >
                          </span>
                          <span v-else class="setlist-chip chip-ghost">titre —</span>
                          <span
                            v-if="t.first_artist"
                            class="setlist-chip chip-artist"
                            :style="{ '--hue': t.artistHue }"
                            :title="t.first_artist.name"
                          >
                            <span class="chip-glyph" aria-hidden="true">A</span>
                            <span class="chip-dot" aria-hidden="true"></span>
                            <span class="chip-name">{{ t.first_artist.name }}</span>
                            <span class="chip-time">{{ formatTime(t.first_artist.time_ms) }}</span>
                          </span>
                          <span v-else class="setlist-chip chip-ghost">artiste —</span>
                        </template>
                      </span>
                    </li>
                  </ol>
                </div>

                <!-- Mobile: actions close the ceremony, after the setlist -->
                <FinishedActions
                  v-if="isMobile"
                  :is-host="isHost"
                  @back="onBackToLobby"
                  @replay="onReplay"
                />
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Desktop sidebar -->
      <aside v-if="!isMobile && phase !== 'countdown' && phase !== 'finished'" class="sidebar">
        <!-- Total scores (always visible, top) -->
        <div class="sidebar-section">
          <h3 class="sidebar-heading text-display">Score total</h3>
          <ScoreBoard :scores="totalScores" :players="playerMap" class="scoreboard-sidebar" />
        </div>

        <!-- Live ranking — only shows players who found something (below scores) -->
        <div v-if="phase === 'playing' && liveRankingFound.length > 0" class="sidebar-section">
          <h3 class="sidebar-heading text-display">Manche en cours</h3>
          <ol class="live-ranking" aria-label="Classement en direct">
            <TransitionGroup name="ranking">
              <li
                v-for="(entry, idx) in liveRankingFound"
                :key="entry.player_id"
                class="ranking-row"
                :class="{
                  'ranking-bonus': entry.match_type === 'bonus',
                  'ranking-partial': entry.match_type === 'title' || entry.match_type === 'artist',
                  'ranking-leader': idx === 0,
                }"
                :style="{ '--hue': getPlayerHue(entry.player_id) }"
              >
                <span class="ranking-pos">{{ idx + 1 }}</span>
                <span class="ranking-avatar" aria-hidden="true"></span>
                <span class="ranking-name">{{ entry.name }}</span>
                <span class="ranking-badge" :class="'match-' + entry.match_type">
                  {{ matchLabel(entry.match_type) }}
                </span>
                <span class="ranking-time">{{ formatTime(entry.time_ms) }}</span>
                <span v-if="entry.points > 0" class="ranking-points">+{{ entry.points }}</span>
              </li>
            </TransitionGroup>
          </ol>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch, watchEffect } from 'vue'
import AnswerInput from './AnswerInput.vue'
import CircularCountdown from './CircularCountdown.vue'
import Countdown from './Countdown.vue'
import FinishedActions from './FinishedActions.vue'
import RoundPodium from './RoundPodium.vue'
import ScoreBoard from './ScoreBoard.vue'
import TrackWaveform from './TrackWaveform.vue'
import { useBreakpoint } from '../composables/useBreakpoint'
import { useSocket } from '../composables/useSocket'
import { useVolume } from '../composables/useVolume'
import { useAmbiance } from '../composables/useAmbiance'
import { getPlayerHue } from '../lib/playerHue'
import { formatTime } from '../lib/time'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import type { Award, FirstFinder, FuzzyResult, MatchInfo, PlayerFoundEvent } from '../types'

const { emit: socketEmit, on: socketOn, off: socketOff } = useSocket()
const { attachMusic } = useVolume()
const { connectAudio: connectAmbianceAudio } = useAmbiance()
const { isMobile } = useBreakpoint()
const auth = useAuthStore()
const roomStore = useRoomStore()
const gameStore = useGameStore()

const answerRef = ref<InstanceType<typeof AnswerInput> | null>(null)
const audioRef = ref<HTMLAudioElement | null>(null)
const locallyFound = ref(false)
const liveFound = ref<
  Array<{ player_id: string; name: string; time_ms: number; match_type: string; points: number }>
>([])
const localAnswer = ref<{
  correct_title: string
  correct_artist: string
  cover_url: string
} | null>(null)
let detachMusic: (() => void) | null = null

const DEFAULT_EXTRACT_DURATION = 30
const REVEAL_WINDOW_SECONDS = 5

watchEffect(() => {
  if (audioRef.value && !detachMusic) {
    // Resume mid-track after a reload so the music matches the timer.
    if (roundElapsedAtStart.value > 0) {
      audioRef.value.currentTime = roundElapsedAtStart.value
    }
    detachMusic = attachMusic(audioRef.value)
    // Wire the audio into the ambiance analyser so --ambiance-intensity pulses
    // with the bass while music plays. Safe because the <audio> declares
    // crossorigin="anonymous" and Deezer's CDN returns ACAO `*` — without
    // that combo the graph would silence (CORS-tainted source). Idempotent
    // per element (the composable dedupes via WeakMap).
    connectAmbianceAudio(audioRef.value)
  } else if (!audioRef.value && detachMusic) {
    detachMusic()
    detachMusic = null
  }
})

function onAudioError() {
  // Telemetry only — surfaces if Deezer ever flips its CORS policy or a
  // preview URL HMAC expires mid-round. Without this listener the user
  // would just see "no sound" with no hint as to why.
  const err = audioRef.value?.error
  console.warn('[blindtest] audio load failed', {
    code: err?.code,
    message: err?.message,
    src: audioRef.value?.currentSrc,
  })
}

const state = computed(() => gameStore.state)
const phase = computed<string>(() => gameStore.state?.phase ?? '')
const totalScores = computed<Record<string, number>>(() => gameStore.state?.total_scores ?? {})

const trackUrl = computed<string>(() => gameStore.state?.track?.preview_url ?? '')

const roundResults = computed(() => gameStore.state?.round_results)

const playingDuration = computed(() => {
  const extract = gameStore.state?.extract_duration ?? DEFAULT_EXTRACT_DURATION
  return Math.max(1, extract - REVEAL_WINDOW_SECONDS)
})

const playElapsed = ref(0)
/** Seconds already gone when the local timer started (non-zero after a
 *  reload mid-round): the ring, the waveform and the audio resume from it. */
const roundElapsedAtStart = ref(0)
let playElapsedHandle: ReturnType<typeof globalThis.setInterval> | null = null

function roundOriginMs(): number {
  // The server ships how long the round has been running (its own clock is
  // monotonic, so an absolute timestamp would be meaningless here). Use it
  // when plausible — a reload mid-round lands with 10s already gone.
  const elapsed = gameStore.state?.round_elapsed_ms
  const now = Date.now()
  if (typeof elapsed === 'number' && elapsed > 0 && elapsed <= playingDuration.value * 1000) {
    return now - elapsed
  }
  return now
}

function startPlayElapsedTimer() {
  stopPlayElapsedTimer()
  const origin = roundOriginMs()
  playElapsed.value = Date.now() - origin
  roundElapsedAtStart.value = Math.floor(playElapsed.value / 1000)
  playElapsedHandle = globalThis.setInterval(() => {
    playElapsed.value = Date.now() - origin
  }, 200)
}

function stopPlayElapsedTimer() {
  if (playElapsedHandle !== null) {
    globalThis.clearInterval(playElapsedHandle)
    playElapsedHandle = null
  }
}

const timeRemaining = computed(() =>
  Math.max(playingDuration.value - Math.floor(playElapsed.value / 1000), 0),
)

const stressLevel = computed<'normal' | 'warning' | 'critical'>(() => {
  if (timeRemaining.value <= 5) return 'critical'
  if (timeRemaining.value <= 10) return 'warning'
  return 'normal'
})

const waveformProgress = computed(() =>
  Math.min(playElapsed.value / (playingDuration.value * 1000), 1),
)

const waveformMarkers = computed<MatchInfo[]>(
  () => gameStore.state?.round_results?.all_matches ?? [],
)

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

// Names are memoised across roster updates: a player who quits mid-game
// keeps their score rows, and those must still read "Bob", not a user id.
const knownNames = ref<Record<string, string>>({})
watch(
  () => roomStore.room?.players,
  (players) => {
    if (!players) return
    const next = { ...knownNames.value }
    for (const p of players) {
      next[p.id] = p.name
    }
    knownNames.value = next
  },
  { immediate: true, deep: true },
)

const playerMap = computed<Record<string, { name: string }>>(() => {
  const map: Record<string, { name: string }> = {}
  for (const [id, name] of Object.entries(knownNames.value)) {
    // eslint-disable-next-line security/detect-object-injection
    map[id] = { name }
  }
  return map
})

const isHost = computed(() => roomStore.isHost)

const isLastRound = computed(() => !!gameStore.state?.is_last_round)

function matchLabel(type: string): string {
  if (type === 'bonus') return 'Titre + Artiste'
  if (type === 'title') return 'Titre \u2713'
  if (type === 'artist') return 'Artiste \u2713'
  return type
}

function matchColor(type: string): string {
  if (type === 'bonus') return 'var(--color-success)'
  if (type === 'title') return 'var(--color-accent)'
  if (type === 'artist') return 'var(--color-warning)'
  return 'var(--color-text-muted)'
}

function isFirstBonus(playerId: string): boolean {
  const first = liveFound.value.find((e) => e.match_type === 'bonus')
  return first?.player_id === playerId
}

interface RankingEntry {
  player_id: string
  name: string
  match_type: string
  time_ms: number
  points: number
}

const liveRankingFound = computed<RankingEntry[]>(() => {
  const typePriority: Record<string, number> = { bonus: 0, title: 1, artist: 1 }
  const playerNames = new Map((roomStore.room?.players ?? []).map((p) => [p.id, p.name]))

  return liveFound.value
    .map((f) => ({
      player_id: f.player_id,
      name: playerNames.get(f.player_id) ?? f.name,
      match_type: f.match_type,
      time_ms: f.time_ms,
      points: f.points,
    }))
    .sort((a, b) => {
      const pa = typePriority[a.match_type] ?? 2
      const pb = typePriority[b.match_type] ?? 2
      if (pa !== pb) return pa - pb
      return a.time_ms - b.time_ms
    })
})

watch(
  phase,
  (newPhase, oldPhase) => {
    if (newPhase === 'playing') {
      startPlayElapsedTimer()
    } else {
      stopPlayElapsedTimer()
    }
    if (newPhase === 'playing' && oldPhase !== 'playing') {
      locallyFound.value = false
      localAnswer.value = null
      answerRef.value?.clearResult()
      // Joining a round already in progress (reload): the state carries the
      // matches broadcast before we were listening.
      liveFound.value = (gameStore.state?.round_matches ?? []).map((m) => ({
        player_id: m.player_id,
        name: playerNameById(m.player_id) || m.name,
        time_ms: m.time_ms,
        match_type: m.match_type,
        points: typeof m.points === 'number' ? m.points : 0,
      }))
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
    payload: { text },
  })
}

const displayAwards = computed<Award[]>(() => gameStore.awards)

// Setlist recap: classify each played track for the ceremony. Semantic color
// says WHAT was found (title/artist/both), player hue says WHO — the exact
// grammar the waveform markers taught during the game.
type SetlistKind = 'parfait' | 'split' | 'title' | 'artist' | 'nobody'

function classifySetlistEntry(
  firstTitle: FirstFinder | null,
  firstArtist: FirstFinder | null,
): SetlistKind {
  if (firstTitle && firstArtist) {
    return firstTitle.player_id === firstArtist.player_id ? 'parfait' : 'split'
  }
  if (firstTitle) return 'title'
  if (firstArtist) return 'artist'
  return 'nobody'
}

const setlist = computed(() => {
  const entries = gameStore.tracklist
  const titleTimes = entries
    .filter((e) => e.first_title)
    .map((e) => e.first_title as FirstFinder)
    .map((f) => f.time_ms)
  const fastestTitleMs = titleTimes.length > 1 ? Math.min(...titleTimes) : null
  return entries.map((e) => {
    const kind = classifySetlistEntry(e.first_title, e.first_artist)
    const parfait = kind === 'parfait'
    return {
      ...e,
      kind,
      titleHue: e.first_title ? getPlayerHue(e.first_title.player_id) : 0,
      artistHue: e.first_artist ? getPlayerHue(e.first_artist.player_id) : 0,
      parfaitMs: parfait ? Math.max(e.first_title?.time_ms ?? 0, e.first_artist?.time_ms ?? 0) : 0,
      isFastestTitle:
        e.first_title !== null &&
        fastestTitleMs !== null &&
        e.first_title.time_ms === fastestTitleMs,
    }
  })
})
const finalDisplayScores = computed<Record<string, number>>(() => {
  const final = gameStore.finalScores
  return Object.keys(final).length > 0 ? final : totalScores.value
})

interface PodiumEntry {
  id: string
  name: string
  score: number
  rank: 1 | 2 | 3
  hue: number
}

const topThree = computed<PodiumEntry[]>(() => {
  const scores = finalDisplayScores.value
  return Object.entries(scores)
    .map(([id, score]) => ({
      id,
      score,
      // eslint-disable-next-line security/detect-object-injection
      name: playerMap.value[id]?.name ?? id,
      hue: getPlayerHue(id),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map((entry, idx) => ({
      ...entry,
      rank: (idx + 1) as 1 | 2 | 3,
    }))
})

const podiumSlots = computed(() => {
  // Display order: 2nd, 1st, 3rd (classic podium layout)
  const second = topThree.value.find((e) => e.rank === 2)
  const first = topThree.value.find((e) => e.rank === 1)
  const third = topThree.value.find((e) => e.rank === 3)
  const result: Array<PodiumEntry | null> = []
  if (topThree.value.length >= 2) result.push(second ?? null)
  else result.push(null)
  result.push(first ?? null)
  if (topThree.value.length >= 3) result.push(third ?? null)
  else result.push(null)
  return result
})

function onBackToLobby() {
  socketEmit('return_to_lobby', { code: roomCode.value })
}

function onReplay() {
  socketEmit('replay_game', { code: roomCode.value })
}

function playerNameById(id: string): string {
  const players = roomStore.room?.players ?? []
  return players.find((p) => p.id === id)?.name ?? id
}

function onPlayerMatch(data: unknown) {
  const d = data as PlayerFoundEvent
  if (!d || typeof d.player_id !== 'string') return
  const matchType = d.match_type ?? 'bonus'
  const points = typeof d.points === 'number' ? d.points : 0
  const existing = liveFound.value.findIndex((e) => e.player_id === d.player_id)
  if (existing >= 0) {
    const updated = [...liveFound.value]
    // eslint-disable-next-line security/detect-object-injection
    updated[existing] = {
      // eslint-disable-next-line security/detect-object-injection
      ...updated[existing],
      time_ms: d.time_ms,
      match_type: matchType,
      points,
    }
    liveFound.value = updated.sort((a, b) => a.time_ms - b.time_ms)
  } else {
    liveFound.value = [
      ...liveFound.value,
      {
        player_id: d.player_id,
        name: playerNameById(d.player_id),
        time_ms: d.time_ms,
        match_type: matchType,
        points,
      },
    ].sort((a, b) => a.time_ms - b.time_ms)
  }
}

function onEventResult(data: unknown) {
  const d = data as FuzzyResult & {
    player_id?: string
    round_points?: number
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
    points: typeof d.round_points === 'number' ? d.round_points : undefined,
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
  socketOn('player_match', onPlayerMatch)
})

onBeforeUnmount(() => {
  socketOff('game_event_result', onEventResult)
  socketOff('player_match', onPlayerMatch)
  stopPlayElapsedTimer()
  detachMusic?.()
  detachMusic = null
})
</script>

<style scoped>
/* === Base layout === */
.blindtest-round {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  width: 100%;
  overflow: hidden;
}

.game-body {
  flex: 1;
  display: flex;
  flex-direction: column;
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
  overflow: visible;
}

/* === Phase transitions === */
.phase-enter-active {
  transition:
    opacity 0.3s var(--ease-smooth),
    transform 0.3s var(--ease-smooth);
}
.phase-leave-active {
  transition:
    opacity 0.2s var(--ease-smooth),
    transform 0.2s var(--ease-smooth);
}
.phase-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.phase-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* === Countdown stage === */
.countdown-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
}

/* === Answer stage === */
.answer-stage {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  /* The stage stretches (flex: 1) to fill the game body — center its
     content vertically so the free height frames the orb/waveform/input
     instead of pooling below them. */
  justify-content: center;
  gap: var(--space-lg);
  width: 100%;
  flex: 1;
}

.hint {
  color: var(--color-accent);
  font-size: var(--text-base);
  letter-spacing: 2px;
  text-transform: uppercase;
  text-shadow: 0 0 12px rgba(var(--color-accent-rgb), 0.35);
}

@media (min-width: 768px) {
  .hint {
    font-size: var(--text-lg);
  }
}

/* === Mystery orb (synthwave sun adaptation) === */
.mystery-orb {
  position: relative;
  width: 170px;
  height: 170px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
}

.mystery-orb .synth-sun {
  position: absolute;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background:
    repeating-linear-gradient(
      180deg,
      transparent 0px,
      transparent 4.5px,
      rgba(var(--color-bg-rgb), 0.92) 4.5px,
      rgba(var(--color-bg-rgb), 0.92) 6px
    ),
    linear-gradient(
      180deg,
      var(--color-warning) 0%,
      var(--color-sun-mid) 38%,
      var(--color-primary) 65%,
      var(--color-secondary) 100%
    );
  box-shadow:
    0 0 24px rgba(var(--color-primary-rgb), 0.6),
    0 0 48px rgba(var(--color-secondary-rgb), 0.35),
    0 0 72px rgba(var(--color-accent-rgb), 0.2);
  animation: sun-breathe 3s ease-in-out infinite;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.mystery-orb .synth-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 50%;
  pointer-events: none;
  mix-blend-mode: screen;
}

.mystery-orb .synth-ring-1 {
  width: 140px;
  height: 140px;
  margin: -70px 0 0 -70px;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    var(--color-accent) 25deg,
    transparent 55deg,
    transparent 180deg,
    var(--color-accent) 205deg,
    transparent 235deg,
    transparent 360deg
  );
  -webkit-mask: radial-gradient(circle, transparent 60%, #000 62%, #000 66%, transparent 68%);
  mask: radial-gradient(circle, transparent 60%, #000 62%, #000 66%, transparent 68%);
  filter: drop-shadow(0 0 5px var(--color-accent));
  animation: ring-cw 5s linear infinite;
}

.mystery-orb .synth-ring-2 {
  width: 180px;
  height: 180px;
  margin: -90px 0 0 -90px;
  background: conic-gradient(
    from 90deg,
    transparent 0deg,
    var(--color-primary) 35deg,
    transparent 75deg,
    transparent 360deg
  );
  -webkit-mask: radial-gradient(circle, transparent 60%, #000 64%, #000 68%, transparent 70%);
  mask: radial-gradient(circle, transparent 60%, #000 64%, #000 68%, transparent 70%);
  filter: drop-shadow(0 0 6px var(--color-primary));
  animation: ring-ccw 8s linear infinite;
}

.mystery-orb .synth-ring-3 {
  width: 220px;
  height: 220px;
  margin: -110px 0 0 -110px;
  background: conic-gradient(
    from 180deg,
    transparent 0deg,
    var(--color-secondary) 20deg,
    transparent 48deg,
    transparent 180deg,
    var(--color-secondary) 200deg,
    transparent 228deg,
    transparent 360deg
  );
  -webkit-mask: radial-gradient(circle, transparent 62%, #000 66%, #000 70%, transparent 72%);
  mask: radial-gradient(circle, transparent 62%, #000 66%, #000 70%, transparent 72%);
  filter: drop-shadow(0 0 6px var(--color-secondary));
  animation: ring-cw 12s linear infinite;
}

.mystery-orb .synth-sonar {
  position: absolute;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 1px solid rgba(var(--color-accent-rgb), 0.3);
  animation: synth-sonar-pulse 3s ease-out infinite;
  pointer-events: none;
}

.orb-symbol {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  color: var(--color-text);
  opacity: 0.7;
  text-shadow:
    0 0 20px rgba(var(--color-accent-rgb), 0.6),
    0 0 40px rgba(var(--color-primary-rgb), 0.4);
  pointer-events: none;
  animation: orb-note-bob 2s ease-in-out infinite;
  position: relative;
  z-index: 3;
}

/* === Found overlay === */
.found-overlay {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-success);
  font-family: var(--font-display);
  font-size: var(--text-lg);
  letter-spacing: 1px;
  text-shadow: 0 0 12px rgba(var(--color-success-rgb), 0.5);
}

.found-check {
  font-size: var(--text-xl);
}

.answer-found :deep(.input-answer) {
  opacity: 0.4;
}

.audio-el {
  display: none;
}

.stage-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.playing-countdown {
  /* Pinned in the game area's top-right corner (the answer stage fills the
     whole content column) — far from the orb's rings and sonar ping. */
  position: absolute;
  top: var(--space-md);
  right: var(--space-md);
  z-index: 2;
}

/* === Live ticker === */
.live-ticker {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-sm);
  width: 100%;
  max-width: 420px;
}

.ticker-pill {
  --hue: 200;
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 0.25rem 0.55rem;
  border-radius: var(--radius-full);
  background: linear-gradient(
    90deg,
    hsla(var(--hue), 85%, 55%, 0.35),
    rgba(var(--color-surface-rgb), 0.9)
  );
  border: 1px solid hsla(var(--hue), 90%, 60%, 0.4);
  box-shadow: 0 0 10px hsla(var(--hue), 90%, 60%, 0.3);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.ticker-avatar {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: hsl(var(--hue), 95%, 62%);
  box-shadow: 0 0 8px hsla(var(--hue), 95%, 62%, 0.7);
}

.ticker-name {
  font-weight: 600;
}

.ticker-match {
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-full);
  line-height: 1.2;
}

.match-bonus {
  background: rgba(var(--color-success-rgb), 0.25);
  color: var(--color-success);
  text-shadow: 0 0 6px rgba(var(--color-success-rgb), 0.4);
}

.match-title {
  background: rgba(var(--color-accent-rgb), 0.2);
  color: var(--color-accent);
  text-shadow: 0 0 6px rgba(var(--color-accent-rgb), 0.4);
}

.match-artist {
  background: rgba(var(--color-warning-rgb), 0.2);
  color: var(--color-warning);
  text-shadow: 0 0 6px rgba(var(--color-warning-rgb), 0.4);
}

.ticker-time {
  font-family: var(--font-display);
  color: var(--color-warning);
  letter-spacing: 1px;
}

.ticker-points,
.ranking-points {
  font-family: var(--font-display);
  font-size: 0.7rem;
  color: var(--color-success);
  text-shadow: 0 0 8px rgba(var(--color-success-rgb), 0.5);
  animation: score-bump 0.4s var(--ease-bounce);
}

.ticker-badge {
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--color-warning);
  text-shadow: 0 0 6px rgba(var(--color-warning-rgb), 0.5);
  white-space: nowrap;
  animation: badge-pulse 1.5s ease-in-out infinite;
}

@keyframes badge-pulse {
  0%,
  100% {
    opacity: 0.8;
  }
  50% {
    opacity: 1;
  }
}

/* === Compact scoreboard (mobile, inside answer stage) === */
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

/* === Reveal === */
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
  box-shadow: 0 4px 30px rgba(var(--color-black-rgb), 0.4);
  border: 2px solid rgba(var(--color-accent-rgb), 0.3);
  transform: scale(0.85);
  transition: transform 0.4s var(--ease-bounce);
}

.anim-reveal-slide .reveal-cover {
  transform: scale(1);
}

.reveal-title {
  font-size: var(--text-2xl);
  color: var(--color-text);
  text-align: center;
  text-shadow:
    0 0 20px rgba(var(--color-accent-rgb), 0.5),
    0 0 40px rgba(var(--color-primary-rgb), 0.3);
}

.reveal-artist {
  color: var(--color-accent);
  font-size: var(--text-lg);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  text-shadow: 0 0 10px rgba(var(--color-accent-rgb), 0.3);
}

/* === Pause stage === */
.pause-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-lg);
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

.pause-label {
  color: var(--color-accent);
  font-size: var(--text-lg);
  letter-spacing: 2px;
  text-shadow: 0 0 12px rgba(var(--color-accent-rgb), 0.3);
  animation: pause-text-pulse 2s ease-in-out infinite;
}

.pause-scoreboard {
  width: 100%;
  max-width: 420px;
}

/* === Finished stage === */
.finished-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xl);
  width: 100%;
  padding: var(--space-lg) 0;
}

.finished-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  width: 100%;
}

.finished-body--desktop {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(320px, 22vw, 420px);
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas:
    'podium side'
    'main side';
  align-items: flex-start;
  gap: clamp(var(--space-lg), 2.5vw, 3rem);
}

.finished-body--desktop .game-podium {
  grid-area: podium;
  justify-self: center;
}

.finished-body--desktop .finished-side {
  grid-area: side;
  align-self: start;
}

.finished-body--desktop .finished-main {
  grid-area: main;
}

.finished-side {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.finished-body--desktop .finished-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: clamp(var(--space-lg), 2vw, var(--space-xl));
  align-items: center;
}

.finished-body--desktop .finished-side {
  width: 100%;
  position: sticky;
  top: var(--space-lg);
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  background: linear-gradient(
    180deg,
    rgba(var(--color-surface-rgb), 0.55),
    rgba(var(--color-surface-rgb), 0.22)
  );
  border: 1px solid rgba(var(--color-accent-rgb), 0.18);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  box-shadow:
    0 20px 50px -24px rgba(var(--color-black-rgb), 0.7),
    0 0 40px -12px rgba(var(--color-accent-rgb), 0.2),
    inset 0 1px 0 rgba(var(--color-white-rgb), 0.05);
}

.finished-body--desktop .finished-side::-webkit-scrollbar {
  width: 6px;
}
.finished-body--desktop .finished-side::-webkit-scrollbar-track {
  background: transparent;
}
.finished-body--desktop .finished-side::-webkit-scrollbar-thumb {
  background: rgba(var(--color-accent-rgb), 0.25);
  border-radius: 3px;
}

.finished-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  align-items: center;
  width: 100%;
}

.finished-title {
  font-size: var(--text-2xl);
  text-align: center;
  animation: finished-title-enter 0.6s var(--ease-bounce) both;
}

/* === Game Podium === */
.game-podium {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm);
  width: 100%;
  max-width: 520px;
  align-items: end;
  padding: 0 var(--space-sm);
}

.podium-block {
  --hue: 200;
  --podium-delay: 0s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-lg) var(--space-sm) 0;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  background: linear-gradient(
    180deg,
    hsla(var(--hue), 80%, 55%, 0.18),
    rgba(var(--color-surface-rgb), 0.9)
  );
  border: 1px solid hsla(var(--hue), 90%, 60%, 0.35);
  border-bottom: none;
  position: relative;
  opacity: 0;
  animation: podium-rise 0.7s var(--ease-bounce) forwards;
  animation-delay: var(--podium-delay);
}

.podium-rank-1 {
  min-height: 190px;
}

.podium-rank-2 {
  min-height: 140px;
}

.podium-rank-3 {
  min-height: 110px;
}

.podium-champion {
  border-color: rgba(var(--color-warning-rgb), 0.5);
  box-shadow:
    0 0 40px rgba(var(--color-warning-rgb), 0.3),
    0 0 70px hsla(var(--hue), 90%, 60%, 0.2),
    inset 0 0 40px rgba(var(--color-warning-rgb), 0.06);
  background: linear-gradient(
    180deg,
    rgba(var(--color-warning-rgb), 0.15),
    hsla(var(--hue), 80%, 55%, 0.1),
    rgba(var(--color-surface-rgb), 0.92)
  );
}

.podium-empty {
  background: linear-gradient(
    180deg,
    rgba(var(--color-white-rgb), 0.03),
    rgba(var(--color-surface-rgb), 0.7)
  );
  border-color: rgba(var(--color-white-rgb), 0.06);
  box-shadow: none;
  opacity: 0;
  animation: podium-rise 0.7s var(--ease-bounce) forwards;
  animation-delay: 0.9s;
}

.podium-empty .podium-name {
  color: var(--color-text-muted);
}

.podium-bar {
  width: 100%;
  height: 6px;
  margin-top: auto;
  background: linear-gradient(
    90deg,
    hsla(var(--hue), 85%, 55%, 0.6),
    hsla(var(--hue), 85%, 65%, 0.3)
  );
  border-radius: 3px 3px 0 0;
}

.podium-champion .podium-bar {
  background: linear-gradient(
    90deg,
    rgba(var(--color-warning-rgb), 0.7),
    rgba(var(--color-primary-rgb), 0.4)
  );
  box-shadow: 0 0 12px rgba(var(--color-warning-rgb), 0.4);
}

.podium-empty .podium-bar {
  background: rgba(var(--color-white-rgb), 0.06);
}

.podium-medal {
  font-size: var(--text-2xl);
  line-height: 1;
}

.podium-champion .podium-medal {
  font-size: var(--text-hero);
  filter: drop-shadow(0 0 12px rgba(var(--color-warning-rgb), 0.6));
}

.podium-crown {
  font-size: var(--text-lg);
  position: absolute;
  top: -6px;
  filter: drop-shadow(0 0 6px rgba(var(--color-warning-rgb), 0.7));
  animation: crown-float 2s ease-in-out infinite;
}

.podium-name {
  font-weight: 700;
  font-size: var(--text-base);
  color: var(--color-text);
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}

.podium-name-champion {
  font-size: var(--text-lg);
  background: linear-gradient(135deg, var(--color-warning), var(--color-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
  filter: drop-shadow(0 0 8px rgba(var(--color-warning-rgb), 0.3));
}

.podium-score {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-sm);
  color: var(--color-warning);
  letter-spacing: 1px;
  text-shadow:
    0 0 10px rgba(var(--color-warning-rgb), 0.45),
    0 0 20px rgba(var(--color-warning-rgb), 0.2);
}

/* === Final Scoreboard === */
.final-scoreboard {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.final-scoreboard-heading {
  font-size: var(--text-lg);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 3px;
  text-align: center;
  margin: 0;
}

/* === Awards === */
.awards-ceremony {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.awards-heading {
  font-size: var(--text-xl);
  color: var(--color-accent);
  text-transform: uppercase;
  letter-spacing: 3px;
  text-shadow: 0 0 20px rgba(var(--color-accent-rgb), 0.4);
  margin: 0;
}

.awards-grid {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-md);
}

.award-card {
  --hue: 200;
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  min-height: 72px;
  background: linear-gradient(
    135deg,
    hsla(var(--hue), 80%, 50%, 0.14),
    rgba(var(--color-surface-rgb), 0.88)
  );
  border: 1px solid hsla(var(--hue), 80%, 55%, 0.3);
  border-radius: var(--radius-lg);
  box-shadow: 0 0 20px hsla(var(--hue), 80%, 55%, 0.15);
  opacity: 0;
  transform: translateY(24px);
  animation: award-slide-in 0.5s var(--ease-bounce) both;
  position: relative;
  overflow: hidden;
}

/* Maestro / first award extra glow + sparkle */
.award-maestro {
  border-color: rgba(var(--color-warning-rgb), 0.5);
  box-shadow:
    0 0 30px rgba(var(--color-warning-rgb), 0.3),
    0 0 60px hsla(var(--hue), 80%, 55%, 0.15);
  background: linear-gradient(
    135deg,
    rgba(var(--color-warning-rgb), 0.12),
    hsla(var(--hue), 80%, 50%, 0.1),
    rgba(var(--color-surface-rgb), 0.9)
  );
}

.award-maestro::before,
.award-maestro::after {
  content: '';
  position: absolute;
  top: -4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  animation: confetti-sparkle 2s ease-in-out infinite;
}

.award-maestro::before {
  left: 15%;
  box-shadow:
    0 0 0 2px rgba(var(--color-warning-rgb), 0.6),
    20px -8px 0 1px rgba(var(--color-primary-rgb), 0.5),
    45px 4px 0 2px rgba(var(--color-accent-rgb), 0.5),
    -10px -12px 0 1px rgba(var(--color-success-rgb), 0.5);
}

.award-maestro::after {
  right: 15%;
  box-shadow:
    0 0 0 2px rgba(var(--color-primary-rgb), 0.5),
    -15px -6px 0 1px rgba(var(--color-warning-rgb), 0.6),
    10px -10px 0 2px rgba(var(--color-accent-rgb), 0.4),
    25px 2px 0 1px rgba(var(--color-success-rgb), 0.5);
  animation-delay: 0.5s;
}

.award-emoji {
  font-size: 2rem;
  flex-shrink: 0;
  filter: drop-shadow(0 0 8px hsla(var(--hue), 80%, 55%, 0.5));
}

.award-body {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.award-title {
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.award-player {
  font-weight: 700;
  font-size: var(--text-sm);
  color: hsl(var(--hue), 85%, 65%);
  text-shadow: 0 0 10px hsla(var(--hue), 85%, 65%, 0.4);
}

.award-detail {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

/* === Zone actions === */
.zone-actions {
  position: sticky;
  bottom: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  padding-bottom: calc(var(--space-md) + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, transparent, rgba(var(--color-bg-rgb), 0.92));
  width: 100%;
}

.zone-actions .btn {
  min-height: 48px;
  min-width: 140px;
}

@media (min-width: 768px) {
  .zone-actions {
    flex-direction: row;
    align-items: center;
  }
}

/* === Desktop sidebar === */
.sidebar {
  display: none;
}

/* === Keyframes === */
@keyframes ring-cw {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes ring-ccw {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(-360deg);
  }
}

@keyframes sun-breathe {
  0%,
  100% {
    transform: scale(1);
    filter: brightness(1);
  }
  50% {
    transform: scale(1.06);
    filter: brightness(1.15);
  }
}

@keyframes orb-note-bob {
  0%,
  100% {
    transform: translateY(-3px);
  }
  50% {
    transform: translateY(3px);
  }
}

@keyframes synth-sonar-pulse {
  0% {
    transform: scale(1);
    opacity: 0.5;
  }
  100% {
    transform: scale(2);
    opacity: 0;
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

@keyframes pause-text-pulse {
  0%,
  100% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
}

.stress-pulse {
  animation: screen-stress 0.8s ease-in-out infinite;
}

@keyframes screen-stress {
  0%,
  100% {
    box-shadow: inset 0 0 0 0 transparent;
  }
  50% {
    box-shadow: inset 0 0 60px rgba(var(--color-error-rgb), 0.12);
  }
}

@keyframes award-slide-in {
  0% {
    opacity: 0;
    transform: translateY(24px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes confetti-sparkle {
  0%,
  100% {
    opacity: 0.4;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

@keyframes podium-rise {
  0% {
    opacity: 0;
    transform: translateY(40px) scaleY(0.6);
  }
  60% {
    opacity: 1;
    transform: translateY(-6px) scaleY(1.03);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scaleY(1);
  }
}

@keyframes crown-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-2px);
  }
}

@keyframes finished-title-enter {
  0% {
    opacity: 0;
    transform: scale(0.8);
  }
  60% {
    transform: scale(1.05);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* === Reduced motion === */
@media (prefers-reduced-motion: reduce) {
  .mystery-orb .synth-ring,
  .mystery-orb .synth-sonar,
  .mystery-orb .synth-sun,
  .orb-symbol,
  .ticker-badge {
    animation: none;
  }
  .pause-indicator {
    animation: none;
  }
  .pause-label {
    animation: none;
  }
  .stress-pulse {
    animation: none;
  }
  .award-card {
    animation: none;
    opacity: 1;
    transform: none;
    filter: none;
  }
  .podium-block,
  .podium-empty {
    animation: none;
    opacity: 1;
    transform: none;
  }
  .podium-crown {
    animation: none;
  }
  .finished-title {
    animation: none;
  }
  .phase-enter-active,
  .phase-leave-active {
    transition: none;
  }
}

/* === Desktop layout — fluid immersive stage === */
.layout-desktop {
  width: 100%;
  height: 100%;
  max-width: none;
  margin: 0;
  padding-inline: clamp(var(--space-md), 3vw, 3rem);
}

.layout-desktop .game-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(260px, 20vw, 320px);
  /* minmax(0, 1fr): the row must not grow past the locked viewport — the
     stage scrolls internally instead of pushing the page. */
  grid-template-rows: minmax(0, 1fr);
  gap: clamp(var(--space-lg), 2.4vw, var(--space-xl));
  align-items: stretch;
  min-height: 0;
}

.layout-desktop .zone-content {
  min-height: 0;
  justify-content: center;
  padding: clamp(var(--space-sm), 2vh, var(--space-lg)) clamp(var(--space-md), 2vw, var(--space-xl));
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(var(--color-white-rgb), 0.15) transparent;
}

/* The answer stage centers within the main column, widened generously.
   Its vertical rhythm scales with the viewport height so a full reveal
   (cover, title, waveform, input, podium) fits a 900px-tall screen. */
.layout-desktop .answer-stage {
  max-width: min(860px, 100%);
  margin-inline: auto;
  gap: clamp(var(--space-sm), 2.2vh, var(--space-lg));
}

.layout-desktop .countdown-stage,
.layout-desktop .pause-stage {
  max-width: min(720px, 100%);
  margin-inline: auto;
}

/* Hero elements breathe on wide screens */
.layout-desktop .mystery-orb {
  width: 260px;
  height: 260px;
}

.layout-desktop .mystery-orb .synth-ring-1 {
  width: 200px;
  height: 200px;
  margin: -100px 0 0 -100px;
}

.layout-desktop .mystery-orb .synth-ring-2 {
  width: 240px;
  height: 240px;
  margin: -120px 0 0 -120px;
}

.layout-desktop .mystery-orb .synth-ring-3 {
  width: 320px;
  height: 320px;
  margin: -160px 0 0 -160px;
}

.layout-desktop .mystery-orb .synth-sun,
.layout-desktop .mystery-orb .synth-sonar {
  width: 140px;
  height: 140px;
}

.layout-desktop .reveal {
  max-width: min(720px, 100%);
  padding: clamp(var(--space-md), 2.4vh, var(--space-xl)) var(--space-lg);
}

.layout-desktop .reveal-cover {
  width: clamp(110px, 17vh, 180px);
  height: clamp(110px, 17vh, 180px);
}

.layout-desktop .reveal-title {
  font-size: clamp(var(--text-2xl), 4vh, var(--text-hero));
}

.layout-desktop .scoreboard-compact {
  display: none;
}

/* Sidebar → frosted-glass neon HUD */
.layout-desktop .sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  position: sticky;
  top: calc(var(--game-header-height, 72px) + var(--space-md));
  align-self: start;
  max-height: calc(100vh - var(--game-header-height, 72px) - var(--space-xl));
  overflow-y: auto;
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  background: linear-gradient(
    180deg,
    rgba(var(--color-surface-rgb), 0.55),
    rgba(var(--color-surface-rgb), 0.22)
  );
  border: 1px solid rgba(var(--color-accent-rgb), 0.18);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  box-shadow:
    0 20px 50px -24px rgba(var(--color-black-rgb), 0.7),
    0 0 40px -12px rgba(var(--color-accent-rgb), 0.2),
    inset 0 1px 0 rgba(var(--color-white-rgb), 0.05);
}

.layout-desktop .sidebar::-webkit-scrollbar {
  width: 6px;
}
.layout-desktop .sidebar::-webkit-scrollbar-track {
  background: transparent;
}
.layout-desktop .sidebar::-webkit-scrollbar-thumb {
  background: rgba(var(--color-accent-rgb), 0.25);
  border-radius: 3px;
}

/* Ultra-wide: give the stage even more presence */
@media (min-width: 1600px) {
  .layout-desktop {
    padding-inline: clamp(var(--space-xl), 5vw, 5rem);
  }
  .layout-desktop .game-body {
    grid-template-columns: minmax(0, 1fr) clamp(300px, 18vw, 360px);
    gap: clamp(var(--space-xl), 3vw, 3rem);
  }
  .layout-desktop .answer-stage {
    max-width: min(960px, 100%);
  }
  .layout-desktop .mystery-orb {
    width: 300px;
    height: 300px;
  }
  .layout-desktop .mystery-orb .synth-ring-2 {
    width: 270px;
    height: 270px;
    margin: -135px 0 0 -135px;
  }
  .layout-desktop .mystery-orb .synth-ring-3 {
    width: 360px;
    height: 360px;
    margin: -180px 0 0 -180px;
  }
}

/* === Finished layout (fluid full-bleed) === */
.layout-finished {
  width: 100%;
  max-width: none;
  margin: 0;
  padding-inline: clamp(var(--space-md), 3vw, 3rem);
}

.layout-finished .game-body {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  min-height: calc(100vh - var(--game-header-height, 72px));
}

.layout-finished .zone-content {
  flex: 1;
  min-height: calc(100vh - var(--game-header-height, 72px));
  padding: clamp(var(--space-lg), 3vh, var(--space-xl)) clamp(var(--space-md), 2vw, var(--space-xl));
  align-items: stretch;
  justify-content: stretch;
}

.layout-finished .finished-stage {
  width: 100%;
  max-width: none;
  flex: 1;
  min-height: calc(100vh - var(--game-header-height, 72px) - var(--space-xl) * 2);
  justify-content: space-evenly;
  gap: clamp(var(--space-lg), 3vh, 2.5rem);
  padding: 0;
}

.layout-finished .finished-title {
  font-size: clamp(var(--text-hero), 6vh, 4.5rem);
}

.layout-finished .finished-body {
  flex: 1;
  min-height: 0;
}

.layout-finished .finished-body--desktop {
  align-items: stretch;
}

.layout-finished .finished-body--desktop .finished-main {
  justify-content: space-evenly;
  gap: clamp(var(--space-lg), 3.5vh, 2.5rem);
}

.layout-finished .game-podium {
  max-width: clamp(520px, 42vw, 760px);
}

.layout-finished .podium-rank-1 {
  min-height: clamp(190px, 26vh, 340px);
}
.layout-finished .podium-rank-2 {
  min-height: clamp(140px, 19vh, 250px);
}
.layout-finished .podium-rank-3 {
  min-height: clamp(110px, 15vh, 200px);
}

.layout-finished .award-card {
  min-height: clamp(72px, 10vh, 130px);
  padding: clamp(var(--space-md), 1.5vh, var(--space-lg))
    clamp(var(--space-md), 2vw, var(--space-lg));
}

.layout-finished .award-emoji {
  font-size: clamp(2rem, 4vh, 3rem);
}

.layout-finished .awards-grid {
  grid-template-columns: repeat(2, 1fr);
}

/* Phones: one award per row (two columns squeeze the titles into three
   lines) and a title that fits on two lines instead of three. */
@media (max-width: 560px) {
  .layout-finished .finished-title {
    font-size: clamp(var(--text-2xl), 9vw, var(--text-hero));
  }
  .layout-finished .awards-grid {
    grid-template-columns: 1fr;
  }
}

.layout-finished .zone-actions {
  max-width: 800px;
  margin: 0 auto;
}

/* 3-column awards on very wide screens */
@media (min-width: 1024px) {
  .layout-finished .awards-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Zone actions desktop layout */
@media (min-width: 768px) {
  .layout-finished .zone-actions .btn {
    min-width: 180px;
  }
}

/* Ultra-wide: podium bigger, awards up to 4 cols, more generous gutters */
@media (min-width: 1600px) {
  .layout-finished {
    padding-inline: clamp(var(--space-xl), 5vw, 5rem);
  }
  .layout-finished .game-podium {
    max-width: clamp(640px, 38vw, 860px);
  }
  .layout-finished .awards-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  .finished-body--desktop {
    grid-template-columns: minmax(0, 1fr) clamp(360px, 20vw, 460px);
    gap: clamp(var(--space-xl), 3vw, 3.5rem);
  }
}

@media (min-width: 2400px) {
  .layout-finished .game-podium {
    max-width: min(1000px, 34vw);
  }
  .layout-finished .awards-grid {
    grid-template-columns: repeat(5, 1fr);
  }
  .finished-body--desktop {
    grid-template-columns: minmax(0, 1fr) clamp(420px, 16vw, 520px);
  }
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.sidebar-heading {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
}

/* === Live ranking === */
.live-ranking {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: relative;
}

.ranking-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  background: rgba(var(--color-surface-rgb), 0.6);
  border-left: 3px solid transparent;
  transition:
    transform 0.4s var(--ease-bounce),
    background 0.3s,
    border-color 0.3s,
    box-shadow 0.3s;
}

.ranking-bonus {
  border-left-color: var(--color-success);
  background: linear-gradient(
    90deg,
    rgba(var(--color-success-rgb), 0.15),
    rgba(var(--color-surface-rgb), 0.6) 60%
  );
  box-shadow: inset 0 0 20px rgba(var(--color-success-rgb), 0.08);
}

.ranking-partial {
  border-left-color: var(--color-accent);
  background: linear-gradient(
    90deg,
    rgba(var(--color-accent-rgb), 0.1),
    rgba(var(--color-surface-rgb), 0.6) 60%
  );
}

.ranking-none {
  opacity: 0.5;
}

.ranking-leader {
  box-shadow:
    inset 0 0 20px rgba(var(--color-success-rgb), 0.12),
    0 0 12px rgba(var(--color-success-rgb), 0.2);
}

.ranking-pos {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  min-width: 20px;
  text-align: center;
}

.ranking-avatar {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(135deg, hsl(var(--hue), 85%, 55%), hsl(var(--hue), 75%, 40%));
  flex-shrink: 0;
}

.ranking-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--text-sm);
}

.ranking-pts {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  color: var(--color-warning);
  text-shadow: 0 0 8px rgba(var(--color-warning-rgb), 0.3);
  min-width: 30px;
  text-align: right;
}

.ranking-badge {
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  font-weight: 600;
  white-space: nowrap;
}

.ranking-time {
  font-family: var(--font-display);
  font-size: 0.65rem;
  color: var(--color-text-muted);
}

/* TransitionGroup move animation */
.ranking-move {
  transition: transform 0.4s var(--ease-bounce);
}

.ranking-enter-active {
  transition:
    opacity 0.3s,
    transform 0.3s var(--ease-bounce);
}

.ranking-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

@media (prefers-reduced-motion: reduce) {
  .ranking-move,
  .ranking-enter-active {
    transition: none;
  }
  .ranking-row {
    transition: none;
  }
}

.sidebar-ticker {
  max-width: none;
  flex-direction: column;
  gap: var(--space-xs);
}

.scoreboard-sidebar :deep(.score-row) {
  padding: var(--space-md) var(--space-md);
  font-size: var(--text-base);
}

.scoreboard-sidebar :deep(.score-name) {
  font-size: var(--text-base);
}

/* === Mobile layout === */
.layout-mobile {
  max-width: 640px;
  margin: 0 auto;
}

.layout-mobile .mystery-orb {
  width: 170px;
  height: 170px;
}

.layout-mobile .mystery-orb .synth-ring-3 {
  width: 180px;
  height: 180px;
  margin: -90px 0 0 -90px;
}

.layout-mobile .podium-rank-1 {
  min-height: 150px;
}

.layout-mobile .podium-rank-2 {
  min-height: 115px;
}

.layout-mobile .podium-rank-3 {
  min-height: 90px;
}

.layout-mobile .podium-champion .podium-medal {
  font-size: var(--text-2xl);
}

/* === Setlist recap === */
.setlist-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
  animation: fade-slide-in 0.3s var(--ease-smooth) 0.9s both;
}

.setlist-heading {
  font-size: var(--text-xl);
  text-transform: uppercase;
  letter-spacing: 3px;
  text-align: center;
  color: var(--color-secondary);
  text-shadow: 0 0 20px rgba(var(--color-secondary-rgb), 0.4);
}

.setlist-kicker {
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  letter-spacing: 1px;
  margin: calc(-1 * var(--space-xs)) 0 0;
}

.setlist {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: var(--space-xs);
}

@media (min-width: 1024px) {
  .setlist {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-xs) var(--space-md);
  }
}

.setlist-row {
  position: relative;
  display: grid;
  grid-template-columns: 1.25rem 2.75rem minmax(0, 1fr) auto;
  align-items: center;
  column-gap: var(--space-sm);
  min-height: 56px;
  padding: var(--space-sm) var(--space-md);
  background: rgba(var(--color-surface-rgb), 0.6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  animation: reveal-slide 0.5s var(--ease-bounce) both;
}

/* The 3px rail carries the outcome color — same grammar as the score rows. */
.setlist-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--setlist-rail, var(--color-border));
  box-shadow: 0 0 10px var(--setlist-rail, transparent);
}

.setlist-row--title {
  --setlist-rail: var(--color-accent);
}
.setlist-row--artist {
  --setlist-rail: var(--color-warning);
}
.setlist-row--parfait {
  --setlist-rail: var(--color-success);
  box-shadow: inset 0 0 20px rgba(var(--color-success-rgb), 0.08);
}
.setlist-row--split::before {
  background: linear-gradient(180deg, var(--color-accent) 0 50%, var(--color-warning) 50% 100%);
  box-shadow: none;
}
.setlist-row--nobody {
  --setlist-rail: rgba(var(--color-white-rgb), 0.08);
}
.setlist-row--nobody .setlist-cover {
  filter: grayscale(0.9);
  opacity: 0.55;
}

.setlist-round {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: right;
}

.setlist-cover {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: var(--radius-sm);
  object-fit: cover;
  border: 1px solid rgba(var(--color-white-rgb), 0.1);
}

.setlist-cover--fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  color: var(--color-accent);
  opacity: 0.6;
  font-family: var(--font-display);
}

.setlist-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.setlist-title {
  font-weight: 700;
  font-size: var(--text-base);
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.setlist-artist {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.setlist-chips {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-end;
}

.setlist-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: var(--radius-full);
  padding: 0.15rem 0.5rem;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text);
  border: 1px solid transparent;
  white-space: nowrap;
}

.chip-title {
  background: rgba(var(--color-accent-rgb), 0.15);
  border-color: rgba(var(--color-accent-rgb), 0.35);
}
.chip-artist {
  background: rgba(var(--color-warning-rgb), 0.15);
  border-color: rgba(var(--color-warning-rgb), 0.35);
}
.chip-parfait {
  background: rgba(var(--color-success-rgb), 0.15);
  border-color: rgba(var(--color-success-rgb), 0.35);
}
.chip-ghost {
  border: 1px dashed rgba(var(--color-white-rgb), 0.15);
  background: transparent;
  color: var(--color-text-muted);
}

.chip-glyph {
  font-family: var(--font-display);
  font-size: var(--text-xs);
}
.chip-title .chip-glyph {
  color: var(--color-accent);
}
.chip-artist .chip-glyph {
  color: var(--color-warning);
}
.chip-parfait .chip-glyph {
  color: var(--color-success);
}

.chip-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: hsl(var(--hue, 200) 95% 62%);
  box-shadow: 0 0 6px hsl(var(--hue, 200) 95% 62% / 0.7);
  flex-shrink: 0;
}

.chip-name {
  max-width: 9ch;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chip-time {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  color: var(--color-warning);
  text-shadow: 0 0 8px rgba(var(--color-warning-rgb), 0.5);
}

@media (prefers-reduced-motion: reduce) {
  .setlist-section,
  .setlist-row {
    animation: none;
  }
}
</style>
