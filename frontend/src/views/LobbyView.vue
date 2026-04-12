<template>
  <div
    v-if="roomStore.room"
    class="lobby"
    :class="{ 'lobby--mobile': isMobile, 'lobby--desktop': !isMobile }"
  >
    <!-- Ambient decoration -->
    <div class="bg-grid" aria-hidden="true"></div>
    <div class="bg-scanlines" aria-hidden="true"></div>
    <div class="bg-orb bg-orb-1" aria-hidden="true"></div>
    <div class="bg-orb bg-orb-2" aria-hidden="true"></div>
    <div class="bg-orb bg-orb-3" aria-hidden="true"></div>

    <!-- Header: Marquee + actions -->
    <header class="lobby-header">
      <div class="marquee">
        <span class="marquee-label">// ROOM CODE</span>
        <button
          type="button"
          class="marquee-code"
          :aria-label="`Copier le code ${roomStore.room.code}`"
          @click="copyCode"
        >
          <span class="marquee-glyphs">{{ roomStore.room.code }}</span>
          <span class="marquee-cursor" aria-hidden="true">_</span>
        </button>
        <p class="marquee-status">
          <span class="pulse-dot" :class="{ ready: canStart }"></span>
          <span>{{ statusLabel }}</span>
          <span class="sep">·</span>
          <span class="count">{{ roomStore.room.players.length }}/10 joueurs</span>
        </p>
        <p class="marquee-hosted">
          <span class="hosted-label">// Hosted by</span>
          <strong class="hosted-name">{{ hostName }}</strong>
        </p>
      </div>

      <nav class="header-chips" aria-label="Actions room">
        <button class="chip chip-accent" @click="copyCode">
          <span class="chip-glyph">⎘</span> Copier
        </button>
        <button v-if="canNativeShare" class="chip chip-accent" @click="nativeShare">
          <span class="chip-glyph">↗</span> Partager
        </button>
        <button class="chip chip-danger" @click="leaveRoom">
          <span class="chip-glyph">↩</span> Quitter
        </button>
      </nav>

      <Transition name="toast">
        <p v-if="toast" class="toast-bubble">{{ toast }}</p>
      </Transition>
    </header>

    <!-- Main two-column grid -->
    <main class="lobby-grid">
      <!-- LEFT: Roster -->
      <section class="panel panel-roster">
        <div class="panel-header">
          <span class="panel-eyebrow">// ROSTER</span>
          <h2 class="panel-title">Guest list</h2>
        </div>
        <PlayerList
          :players="roomStore.room.players"
          :can-kick="roomStore.isHost"
          @kick="kickPlayer"
        />
        <div v-if="emptySlots > 0" class="slots-hint">
          {{ emptySlots }} place{{ emptySlots > 1 ? 's' : '' }} libre{{ emptySlots > 1 ? 's' : '' }}
        </div>
      </section>

      <!-- RIGHT: Console -->
      <section v-if="roomStore.isHost" class="panel panel-console">
        <div class="panel-header">
          <span class="panel-eyebrow">// CONSOLE</span>
          <h2 class="panel-title">Réglages</h2>
        </div>

        <div class="field">
          <label class="field-label">Mode</label>
          <div class="mode-grid">
            <button
              v-for="mode in MODES"
              :key="mode.id"
              type="button"
              class="mode-card"
              :class="[`mode-${mode.id}`, { active: gameMode === mode.id }]"
              @click="setMode(mode.id)"
            >
              <span class="mode-emoji">{{ mode.emoji }}</span>
              <span class="mode-name">{{ mode.label }}</span>
              <span class="mode-tag">{{ mode.tag }}</span>
              <span class="mode-motif" aria-hidden="true">
                <template v-if="mode.id === 'blindtest'">
                  <span class="eq-bar"></span>
                  <span class="eq-bar"></span>
                  <span class="eq-bar"></span>
                  <span class="eq-bar"></span>
                </template>
                <template v-else-if="mode.id === 'karaoke'">
                  <span class="mic-dot"></span>
                  <span class="mic-dot"></span>
                  <span class="mic-dot"></span>
                </template>
                <template v-else>
                  <span class="chain-dot"></span>
                  <span class="chain-dot"></span>
                  <span class="chain-dot"></span>
                </template>
              </span>
            </button>
          </div>
        </div>

        <div v-if="gameMode === 'karaoke'" class="field field-inline">
          <label class="field-label">Variante</label>
          <div class="seg-group">
            <button
              type="button"
              class="seg"
              :class="{ active: karaokeVariant === 'classic' }"
              @click="setKaraokeVariant('classic')"
            >
              Classique
            </button>
            <button
              type="button"
              class="seg"
              :class="{ active: karaokeVariant === 'progressive' }"
              @click="setKaraokeVariant('progressive')"
            >
              Progressif
            </button>
          </div>
        </div>

        <div class="field field-inline">
          <label class="field-label">Manches</label>
          <div class="seg-group seg-group-tight">
            <button
              v-for="n in ROUND_OPTIONS"
              :key="n"
              type="button"
              class="seg"
              :class="{ active: numRounds === n }"
              @click="setNumRounds(n)"
            >
              {{ n }}
            </button>
          </div>
        </div>

        <div class="field">
          <label class="field-label">Genres</label>
          <GenreSelector @update="onGenresUpdate" />
        </div>
      </section>

      <section v-else class="panel panel-waiting">
        <div class="waiting-core">
          <div class="waiting-synth" aria-hidden="true">
            <div class="synth-horizon"></div>
            <div class="synth-ring synth-ring-3"></div>
            <div class="synth-ring synth-ring-2"></div>
            <div class="synth-ring synth-ring-1"></div>
            <div class="synth-sun"></div>
          </div>
          <span class="waiting-eyebrow">// STANDBY</span>
          <p class="waiting-title">En attente</p>
          <p class="waiting-sub">
            <span class="waiting-hostedby">Hosted by</span>
            <strong class="waiting-hostname">{{ hostName }}</strong>
          </p>

          <dl class="waiting-readout">
            <div class="readout-row">
              <dt>Mode</dt>
              <dd>
                <span class="readout-emoji">{{ displayMode.emoji }}</span>
                {{ displayMode.label }}
              </dd>
            </div>
            <div class="readout-row">
              <dt>Manches</dt>
              <dd>{{ displayRounds }}</dd>
            </div>
            <div v-if="displayGenres.length > 0" class="readout-row readout-row-genres">
              <dt>Genres</dt>
              <dd class="genres-dd">
                <span
                  v-for="g in displayGenres"
                  :key="g.key"
                  class="genre-pill"
                  :class="`chip-${getGenreColor(g.key)}`"
                >
                  <span class="pill-label">{{ getGenreLabel(g.key) }}</span>
                  <span class="pill-dots" aria-hidden="true">
                    <span
                      v-for="l in 4"
                      :key="l"
                      class="pill-dot"
                      :class="{ 'pill-dot-on': g.level >= l }"
                    ></span>
                  </span>
                </span>
              </dd>
            </div>
          </dl>

          <p class="waiting-typing">L'hôte règle l'ambiance<span class="dot-pulse">...</span></p>
        </div>
      </section>
    </main>

    <!-- Footer CTA -->
    <footer v-if="roomStore.isHost" class="lobby-footer">
      <button class="btn-launch" :disabled="!canStart" @click="startGame">
        <span class="launch-arrow">▶</span>
        <span class="launch-label">Lancer la soirée</span>
        <span class="launch-meta">
          <span class="meta-item">
            <span class="meta-emoji">{{ currentMode.emoji }}</span>
            {{ currentMode.label }}
          </span>
          <span class="meta-sep" aria-hidden="true">·</span>
          <span class="meta-item">{{ numRounds }} manches</span>
          <span class="meta-sep" aria-hidden="true">·</span>
          <span class="meta-item">{{ roomStore.room.players.length }}/10</span>
        </span>
      </button>
      <p v-if="!canStart" class="launch-hint">Il faut au moins 2 joueurs pour commencer</p>
    </footer>

    <p v-if="errorMsg" class="feedback feedback-wrong error-banner">{{ errorMsg }}</p>

    <ConfirmDialog
      :open="confirmLeaveOpen"
      title="Quitter la room ?"
      message="Tu vas retourner à l'écran d'accueil. Tu pourras toujours rejoindre à nouveau avec le code."
      confirm-text="Quitter"
      variant="danger"
      @confirm="onConfirmLeave"
      @cancel="confirmLeaveOpen = false"
    />

    <ConfirmDialog
      :open="confirmKickOpen"
      :title="`Exclure ${kickTarget?.name ?? ''} ?`"
      message="Ce joueur sera retiré de la room immédiatement."
      confirm-text="Exclure"
      variant="danger"
      @confirm="onConfirmKick"
      @cancel="cancelKick"
    />

    <ConfirmDialog
      :open="kickedNoticeOpen"
      title="Tu as été exclu"
      message="L'hôte t'a retiré de la room. Tu vas retourner à l'accueil."
      confirm-text="OK"
      cancel-text=""
      variant="danger"
      @confirm="onAcknowledgeKicked"
      @cancel="onAcknowledgeKicked"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useSocket } from '../composables/useSocket'
import { useBreakpoint } from '../composables/useBreakpoint'
import PlayerList from '../components/PlayerList.vue'
import GenreSelector from '../components/GenreSelector.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { getGenreLabel, getGenreColor } from '../lib/genres'
import type { RoomState, GameState, Player } from '../types'

type GameModeId = 'blindtest' | 'karaoke' | 'telephone'
type KaraokeVariant = 'classic' | 'progressive'

const MODES: ReadonlyArray<{
  id: GameModeId
  label: string
  emoji: string
  tag: string
}> = [
  { id: 'blindtest', label: 'Blindtest', emoji: '🎵', tag: 'Devine le titre' },
  { id: 'karaoke', label: 'Karaoké', emoji: '🎤', tag: 'Mystère chantant' },
  { id: 'telephone', label: 'Téléphone', emoji: '📞', tag: 'Gartic Phone musical' },
]

const ROUND_OPTIONS = [3, 5, 10, 15] as const

const props = defineProps<{ code: string }>()
const router = useRouter()
const roomStore = useRoomStore()
const gameStore = useGameStore()
const {
  connect: socketConnect,
  emit: socketEmit,
  on,
  off,
  disconnect: socketDisconnect,
} = useSocket()

const auth = useAuthStore()
const gameMode = ref<GameModeId>('blindtest')
const numRounds = ref(10)
const karaokeVariant = ref<KaraokeVariant>('classic')
const errorMsg = ref('')
const toast = ref('')
const canNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

const { isMobile } = useBreakpoint()

const canStart = computed(() => (roomStore.room?.players.length ?? 0) >= 2)
const emptySlots = computed(() => Math.max(0, 10 - (roomStore.room?.players.length ?? 0)))
const statusLabel = computed(() => (canStart.value ? 'Prêt à lancer' : 'En attente de joueurs'))
/** Host's local current mode (used by the launch CTA). */
const currentMode = computed(() => MODES.find((m) => m.id === gameMode.value) ?? MODES[0])

/** Spectator readout: use server-synced room settings (host uses local refs). */
const displayMode = computed(() => {
  const modeId = roomStore.room?.settings?.game_mode ?? 'blindtest'
  return MODES.find((m) => m.id === modeId) ?? MODES[0]
})
const displayRounds = computed(() => roomStore.room?.settings?.num_rounds ?? 10)
const displayGenres = computed(() => {
  const raw = roomStore.room?.settings?.genres
  if (!raw || typeof raw !== 'object') return [] as Array<{ key: string; level: number }>
  return Object.entries(raw).map(([key, level]) => ({ key, level: Number(level) || 2 }))
})
const hostName = computed(() => roomStore.room?.players.find((p) => p.is_host)?.name ?? 'Host')

const confirmLeaveOpen = ref(false)
const confirmKickOpen = ref(false)
const kickTarget = ref<Player | null>(null)
const kickedNoticeOpen = ref(false)

let toastTimer: ReturnType<typeof setTimeout> | null = null
function showToast(message: string) {
  toast.value = message
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = ''
  }, 2000)
}

async function copyCode() {
  if (!roomStore.room) return
  try {
    await navigator.clipboard.writeText(roomStore.room.code)
    showToast('Code copié !')
  } catch {
    showToast('Impossible de copier')
  }
}

async function nativeShare() {
  if (!roomStore.room || !navigator.share) return
  try {
    await navigator.share({
      title: 'ChantePaFo',
      text: `Rejoins ma partie ChantePaFo avec le code ${roomStore.room.code} !`,
      url: window.location.href,
    })
  } catch {
    // user cancelled share — silent
  }
}

function leaveRoom() {
  if (!roomStore.room) return
  confirmLeaveOpen.value = true
}

function onConfirmLeave() {
  confirmLeaveOpen.value = false
  // Disconnecting triggers the server-side _handle_disconnect which
  // calls svc.leave_room and broadcasts room_updated to the other players.
  socketDisconnect()
  roomStore.clearRoom()
  router.push('/')
}

function updateSettings() {
  socketEmit('update_settings', {
    code: props.code,
    settings: {
      game_mode: gameMode.value,
      num_rounds: numRounds.value,
      karaoke_variant: karaokeVariant.value,
    },
  })
}

function setMode(mode: GameModeId) {
  if (gameMode.value === mode) return
  gameMode.value = mode
  updateSettings()
}

function setNumRounds(n: number) {
  if (numRounds.value === n) return
  numRounds.value = n
  updateSettings()
}

function setKaraokeVariant(v: KaraokeVariant) {
  if (karaokeVariant.value === v) return
  karaokeVariant.value = v
  updateSettings()
}

function onGenresUpdate(genres: Record<string, number>) {
  socketEmit('update_settings', {
    code: props.code,
    settings: { genres },
  })
}

function startGame() {
  socketEmit('start_game', { code: props.code })
}

function kickPlayer(playerId: string) {
  const player = roomStore.room?.players.find((p) => p.id === playerId)
  if (!player) return
  kickTarget.value = player
  confirmKickOpen.value = true
}

function onConfirmKick() {
  if (kickTarget.value) {
    socketEmit('kick_player', { code: props.code, player_id: kickTarget.value.id })
  }
  confirmKickOpen.value = false
  kickTarget.value = null
}

function cancelKick() {
  confirmKickOpen.value = false
  kickTarget.value = null
}

function onRoomUpdated(data: unknown) {
  roomStore.setRoom(data as RoomState)
}

function onGameState(data: unknown) {
  gameStore.setState(data as GameState)
  router.push(`/${props.code}/play`)
}

function onError(data: unknown) {
  const d = data as { message?: string }
  errorMsg.value = d.message ?? 'Erreur inconnue'
}

function onPlayerKicked(data: unknown) {
  const d = data as { player_id?: string }
  if (d.player_id === auth.userId) {
    kickedNoticeOpen.value = true
  }
}

function onAcknowledgeKicked() {
  kickedNoticeOpen.value = false
  roomStore.clearRoom()
  router.push('/')
}

onMounted(async () => {
  // Deep-link guard: a direct navigation or refresh on /:code lands here
  // without running createRoom/joinRoom, so the socket singleton may be
  // null. Without a token we can't authenticate — send the user home.
  if (!auth.token) {
    router.replace('/')
    return
  }

  // Ensure the socket is connected BEFORE registering listeners or emitting
  // join_room. connect() is idempotent (no-op if already connected) so the
  // happy path from HomeView is unaffected.
  socketConnect(auth.token)

  // Register event listeners before emitting so we don't miss any events.
  on('room_updated', onRoomUpdated)
  on('game_state', onGameState)
  on('game_started', onGameState)
  on('error', onError)
  on('player_kicked', onPlayerKicked)

  // Enter the Socket.IO room (fixes race where the host's initial
  // join_room was sent before the WebSocket was fully connected).
  socketEmit('join_room', { code: props.code })

  // Fetch current room state to catch any updates missed during navigation.
  const resp = await auth.authFetch(`/api/rooms/${props.code}`)
  if (resp.ok) {
    const data = await resp.json()
    roomStore.setRoom(data.room)
  }
})

onUnmounted(() => {
  off('room_updated', onRoomUpdated)
  off('game_state', onGameState)
  off('game_started', onGameState)
  off('error', onError)
  off('player_kicked', onPlayerKicked)
})
</script>

<style scoped>
/* =========================================
   LOBBY — NEON BACKSTAGE
   =========================================
   Asymmetric 2-col on desktop, dense stack on mobile.
   Leans hard on Righteous, uppercase terminal labels,
   per-mode accents, and pulsing ambient orbs.
   ========================================= */

/* Full-bleed layout — the lobby OCCUPIES the entire viewport on desktop.
   No max-width, no centered box. Everything (background orbs, grid, content)
   stretches edge-to-edge so there's no "artificial cut" on wide monitors.
   Mobile (<900px): natural scroll, content stacks, footer is fixed at bottom.
   Desktop (>=900px): locked to 100vh, page itself NEVER scrolls.
                      Panels scroll internally if their content overflows. */
.lobby {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  width: 100%;
  padding: clamp(1rem, 2.5vw, 2rem) clamp(1rem, 3.5vw, 3rem);
  gap: clamp(1rem, 2vw, 1.5rem);
  isolation: isolate;
}

/* ===== Ambient background layers ===== */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(var(--color-accent-rgb), 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(var(--color-accent-rgb), 0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse at center top, #000 30%, transparent 75%);
  pointer-events: none;
  z-index: -2;
}
/* Horizontal CRT scanlines — the tiny detail that sells the synthwave feel */
.bg-scanlines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    180deg,
    transparent 0px,
    transparent 2px,
    rgba(var(--color-black-rgb), 0.14) 3px,
    transparent 4px
  );
  mask-image: radial-gradient(ellipse at center, #000 40%, transparent 100%);
  -webkit-mask-image: radial-gradient(ellipse at center, #000 40%, transparent 100%);
  mix-blend-mode: overlay;
  pointer-events: none;
  z-index: -2;
}
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  z-index: -1;
  opacity: 0.55;
  mix-blend-mode: screen;
}
/* Positions use % + min()/max() so orbs spread nicely across any viewport
   width — from a narrow 900px laptop to a 3440px ultra-wide. */
.bg-orb-1 {
  top: -5%;
  left: -3%;
  width: clamp(280px, 22vw, 480px);
  height: clamp(280px, 22vw, 480px);
  background: radial-gradient(circle, var(--color-primary) 0%, transparent 65%);
  animation: orb-drift 18s ease-in-out infinite;
}
.bg-orb-2 {
  top: 25%;
  right: -4%;
  width: clamp(320px, 26vw, 560px);
  height: clamp(320px, 26vw, 560px);
  background: radial-gradient(circle, var(--color-accent) 0%, transparent 65%);
  animation: orb-drift 22s ease-in-out infinite reverse;
}
.bg-orb-3 {
  bottom: -8%;
  left: 35%;
  width: clamp(300px, 24vw, 520px);
  height: clamp(300px, 24vw, 520px);
  background: radial-gradient(circle, var(--color-secondary) 0%, transparent 65%);
  animation: orb-drift 26s ease-in-out infinite;
}
@keyframes orb-drift {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.5;
  }
  50% {
    transform: translate(40px, -30px) scale(1.08);
    opacity: 0.65;
  }
}

/* ===== Header / Marquee ===== */
.lobby-header {
  position: relative;
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-md);
  align-items: end;
  animation: slam-in 0.7s var(--ease-bounce) both;
}
.marquee {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-xs);
}
.marquee-label {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 4px;
  color: var(--color-accent);
  text-transform: uppercase;
  opacity: 0.75;
}
.marquee-code {
  display: inline-flex;
  align-items: center;
  gap: 0.15em;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: var(--font-display);
  font-size: clamp(3.2rem, 10vw, 6.5rem);
  line-height: 0.9;
  letter-spacing: 0.08em;
  color: var(--color-text);
  text-transform: uppercase;
  background-image: linear-gradient(
    180deg,
    var(--color-text) 0%,
    var(--color-accent) 55%,
    var(--color-primary) 100%
  );
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 24px rgba(var(--color-accent-rgb), 0.35))
    drop-shadow(0 0 60px rgba(var(--color-primary-rgb), 0.22));
  transition:
    filter 0.25s,
    transform 0.15s;
}
.marquee-code:hover {
  filter: drop-shadow(0 0 32px rgba(var(--color-accent-rgb), 0.55))
    drop-shadow(0 0 80px rgba(var(--color-primary-rgb), 0.35));
}
.marquee-code:active {
  transform: scale(0.98);
}
.marquee-glyphs {
  display: inline-block;
}
.marquee-cursor {
  display: inline-block;
  font-weight: 700;
  color: var(--color-accent);
  -webkit-text-fill-color: var(--color-accent);
  animation: blink 1.1s steps(1) infinite;
  margin-left: 0.08em;
}
@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  51%,
  100% {
    opacity: 0;
  }
}
.marquee-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-top: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 600;
}
.marquee-status .sep {
  opacity: 0.4;
}
.marquee-status .count {
  color: var(--color-accent);
}
.marquee-hosted {
  display: inline-flex;
  align-items: baseline;
  gap: 0.45rem;
  margin-top: 0.2rem;
  font-size: var(--text-sm);
}
.hosted-label {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 3px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  opacity: 0.6;
}
.hosted-name {
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--color-warning);
  letter-spacing: 2px;
  text-transform: uppercase;
  text-shadow: 0 0 14px rgba(var(--color-warning-rgb), 0.4);
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-warning);
  box-shadow: 0 0 10px var(--color-warning);
  animation: pulse-dot 1.6s ease-in-out infinite;
}
.pulse-dot.ready {
  background: var(--color-success);
  box-shadow: 0 0 12px var(--color-success);
}
@keyframes pulse-dot {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.4);
    opacity: 0.6;
  }
}

/* ===== Header chips ===== */
.header-chips {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 1rem;
  background: rgba(var(--color-white-rgb), 0.03);
  border: 1px solid rgba(var(--color-white-rgb), 0.1);
  border-radius: var(--radius-full);
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  backdrop-filter: blur(12px);
  transition:
    background 0.15s,
    border-color 0.15s,
    transform 0.1s;
}
.chip:hover {
  background: rgba(var(--color-white-rgb), 0.06);
  border-color: rgba(var(--color-white-rgb), 0.22);
  transform: translateY(-1px);
}
.chip:active {
  transform: translateY(0);
}
.chip-glyph {
  font-size: 1.1em;
  color: var(--color-accent);
}
.chip-accent:hover {
  border-color: rgba(var(--color-accent-rgb), 0.5);
  box-shadow: 0 0 18px rgba(var(--color-accent-rgb), 0.15);
}
.chip-danger .chip-glyph {
  color: var(--color-error);
}
.chip-danger:hover {
  border-color: rgba(var(--color-error-rgb), 0.45);
  box-shadow: 0 0 18px rgba(var(--color-error-rgb), 0.15);
}

.toast-bubble {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: var(--space-sm);
  padding: 0.4rem 0.9rem;
  background: rgba(var(--color-accent-rgb), 0.12);
  border: 1px solid rgba(var(--color-accent-rgb), 0.35);
  border-radius: var(--radius-full);
  color: var(--color-accent);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  box-shadow: 0 0 24px rgba(var(--color-accent-rgb), 0.25);
}
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.2s,
    transform 0.2s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ===== Main grid ===== */
.lobby-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-md);
  align-items: start;
}
@media (min-width: 900px) {
  .lobby-grid {
    /* Roster stays compact-ish, console takes the rest of the full viewport */
    grid-template-columns: minmax(280px, 0.7fr) minmax(0, 2fr);
    gap: clamp(1rem, 1.8vw, 1.75rem);
    align-items: stretch;
  }
}
/* Ultra-wide: cap roster growth, let console breathe */
@media (min-width: 1600px) {
  .lobby-grid {
    grid-template-columns: minmax(320px, 0.55fr) minmax(0, 2.4fr);
  }
}

/* ===== Panels ===== */
.panel {
  position: relative;
  background: linear-gradient(
    160deg,
    rgba(var(--color-surface-rgb), 0.85) 0%,
    rgba(var(--color-surface-rgb), 0.55) 100%
  );
  border: 1px solid rgba(var(--color-white-rgb), 0.08);
  border-radius: var(--radius-lg);
  padding: clamp(1.1rem, 2.5vw, 1.8rem);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow:
    0 20px 60px rgba(var(--color-black-rgb), 0.4),
    inset 0 1px 0 rgba(var(--color-white-rgb), 0.06);
  animation: rise-in 0.6s var(--ease-bounce) 0.15s both;
}
.panel::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    135deg,
    rgba(var(--color-accent-rgb), 0.35),
    transparent 40%,
    transparent 60%,
    rgba(var(--color-primary-rgb), 0.35)
  );
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  opacity: 0.8;
}
.panel-roster {
  animation-delay: 0.2s;
}
.panel-console {
  animation-delay: 0.3s;
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-bottom: var(--space-md);
}
.panel-eyebrow {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 3px;
  color: var(--color-accent);
  text-transform: uppercase;
  opacity: 0.75;
}
.panel-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
}

.slots-hint {
  margin-top: var(--space-md);
  padding: 0.5rem 0.8rem;
  border: 1px dashed rgba(var(--color-white-rgb), 0.1);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  text-align: center;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* ===== Fields / Console ===== */
.field {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.field-inline {
  gap: 0.5rem;
}
.field-label {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 3px;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

/* ===== Mode cards ===== */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.6rem;
}
.mode-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  padding: 0.85rem 0.9rem;
  background: rgba(var(--color-bg-rgb), 0.55);
  border: 1px solid rgba(var(--color-white-rgb), 0.08);
  border-radius: var(--radius-md);
  cursor: pointer;
  overflow: hidden;
  transition:
    transform 0.15s,
    border-color 0.2s,
    background 0.2s;
  --mode-accent: var(--color-accent);
}
.mode-card.mode-blindtest {
  --mode-accent: var(--color-accent);
}
.mode-card.mode-karaoke {
  --mode-accent: var(--color-primary);
}
.mode-card.mode-telephone {
  --mode-accent: var(--color-secondary);
}
.mode-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, var(--mode-accent) 0%, transparent 60%);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}
.mode-card:hover {
  transform: translateY(-2px);
  border-color: rgba(var(--color-white-rgb), 0.18);
}
.mode-card:hover::after {
  opacity: 0.15;
}
.mode-card.active {
  border-color: var(--mode-accent);
  background: rgba(var(--color-bg-rgb), 0.75);
  box-shadow:
    0 0 0 1px var(--mode-accent),
    0 0 30px color-mix(in srgb, var(--mode-accent) 30%, transparent);
}
.mode-card.active::after {
  opacity: 0.22;
}
.mode-emoji {
  font-size: 1.6rem;
  line-height: 1;
}
.mode-name {
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 1px;
}
.mode-tag {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 600;
}
.mode-card.active .mode-tag {
  color: var(--mode-accent);
}

/* ===== Mode motifs (per-mode animated decoration, top-right corner) ===== */
.mode-motif {
  position: absolute;
  top: 0.55rem;
  right: 0.6rem;
  display: flex;
  align-items: flex-end;
  gap: 2.5px;
  height: 14px;
  opacity: 0.45;
  transition: opacity 0.25s;
  pointer-events: none;
}
.mode-card.active .mode-motif {
  opacity: 1;
}

/* Blindtest — equalizer bars */
.eq-bar {
  width: 2.5px;
  background: var(--mode-accent);
  border-radius: 1px;
  box-shadow: 0 0 6px var(--mode-accent);
  transform-origin: bottom;
}
.eq-bar:nth-child(1) {
  height: 40%;
}
.eq-bar:nth-child(2) {
  height: 80%;
}
.eq-bar:nth-child(3) {
  height: 55%;
}
.eq-bar:nth-child(4) {
  height: 95%;
}
.mode-card.active .eq-bar {
  animation: eq-pulse 0.9s ease-in-out infinite;
}
.mode-card.active .eq-bar:nth-child(1) {
  animation-delay: 0s;
}
.mode-card.active .eq-bar:nth-child(2) {
  animation-delay: 0.15s;
}
.mode-card.active .eq-bar:nth-child(3) {
  animation-delay: 0.3s;
}
.mode-card.active .eq-bar:nth-child(4) {
  animation-delay: 0.45s;
}
@keyframes eq-pulse {
  0%,
  100% {
    transform: scaleY(0.5);
  }
  50% {
    transform: scaleY(1);
  }
}

/* Karaoke — vertical mic dots bouncing like voice pulses */
.mic-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--mode-accent);
  box-shadow: 0 0 6px var(--mode-accent);
  align-self: center;
}
.mode-card.active .mic-dot {
  animation: mic-bounce 1.1s ease-in-out infinite;
}
.mode-card.active .mic-dot:nth-child(1) {
  animation-delay: 0s;
}
.mode-card.active .mic-dot:nth-child(2) {
  animation-delay: 0.18s;
}
.mode-card.active .mic-dot:nth-child(3) {
  animation-delay: 0.36s;
}
@keyframes mic-bounce {
  0%,
  100% {
    transform: translateY(3px);
    opacity: 0.55;
  }
  50% {
    transform: translateY(-3px);
    opacity: 1;
  }
}

/* Téléphone — chain relay, dots filling in sequence */
.chain-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: transparent;
  border: 1.5px solid var(--mode-accent);
  box-shadow: 0 0 4px var(--mode-accent);
  align-self: center;
  transition:
    background 0.2s,
    box-shadow 0.2s;
}
.mode-card.active .chain-dot {
  animation: chain-relay 1.6s ease-in-out infinite;
}
.mode-card.active .chain-dot:nth-child(1) {
  animation-delay: 0s;
}
.mode-card.active .chain-dot:nth-child(2) {
  animation-delay: 0.3s;
}
.mode-card.active .chain-dot:nth-child(3) {
  animation-delay: 0.6s;
}
@keyframes chain-relay {
  0%,
  60%,
  100% {
    background: transparent;
    box-shadow: 0 0 4px var(--mode-accent);
  }
  30% {
    background: var(--mode-accent);
    box-shadow:
      0 0 10px var(--mode-accent),
      0 0 18px var(--mode-accent);
  }
}

/* ===== Segmented group ===== */
.seg-group {
  display: inline-flex;
  padding: 0.25rem;
  background: rgba(var(--color-bg-rgb), 0.6);
  border: 1px solid rgba(var(--color-white-rgb), 0.08);
  border-radius: var(--radius-full);
  gap: 0.15rem;
  width: fit-content;
}
.seg-group-tight {
  padding: 0.2rem;
}
.seg {
  min-width: 3rem;
  padding: 0.45rem 1rem;
  background: transparent;
  border: none;
  border-radius: var(--radius-full);
  color: var(--color-text-muted);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
  transition:
    color 0.2s,
    background 0.2s,
    transform 0.1s;
}
.seg:hover {
  color: var(--color-text);
}
.seg.active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  color: var(--color-text);
  box-shadow: 0 4px 18px rgba(var(--color-primary-rgb), 0.35);
}

/* ===== Waiting panel ===== */
.panel-waiting {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.waiting-core {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  text-align: center;
  max-width: 320px;
}

.waiting-hostedby {
  font-size: var(--text-xs);
  letter-spacing: 2px;
  text-transform: uppercase;
  opacity: 0.6;
  margin-right: 0.4rem;
}
.waiting-hostname {
  font-family: var(--font-display);
  color: var(--color-accent);
  letter-spacing: 1px;
  text-shadow: 0 0 12px rgba(var(--color-accent-rgb), 0.4);
}

.waiting-readout {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  margin: 1.2rem 0 0.5rem;
  padding: 0;
}
.readout-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0.55rem 0.85rem;
  background: rgba(var(--color-bg-rgb), 0.6);
  border: 1px solid rgba(var(--color-white-rgb), 0.06);
  border-radius: var(--radius-md);
  gap: 0.75rem;
}
.readout-row dt {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 2px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin: 0;
}
.readout-row dd {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--color-text);
  letter-spacing: 1px;
  text-align: right;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.readout-emoji {
  font-size: 1.15em;
}

/* Multi-line row for genres — label on top, pills wrap below */
.readout-row-genres {
  flex-direction: column;
  align-items: stretch;
  gap: 0.5rem;
}
.readout-row-genres dt {
  text-align: left;
}
.genres-dd {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  text-align: left;
  max-height: 110px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(var(--color-white-rgb), 0.15) transparent;
}
.genre-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.22rem 0.55rem;
  border-radius: var(--radius-full);
  font-family: var(--font-body);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  line-height: 1.4;
}
.pill-label {
  font-family: var(--font-display);
}
.pill-dots {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.pill-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  border: 1px solid currentColor;
}
.pill-dot-on {
  background: currentColor;
  box-shadow: 0 0 5px currentColor;
}

.waiting-typing {
  margin-top: 0.4rem;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.dot-pulse {
  display: inline-block;
  animation: dot-pulse 1.4s steps(4, end) infinite;
  overflow: hidden;
  vertical-align: bottom;
  white-space: nowrap;
  width: 1.2em;
}
@keyframes dot-pulse {
  0% {
    width: 0;
  }
  100% {
    width: 1.2em;
  }
}
/* ===== Waiting spinner — Synthwave sun rising over neon horizon =====
   Pure 80s Outrun iconography:
   - A circular "sun" with yellow→pink→purple gradient cut by horizontal
     dark bands, glowing pink. Static but pulses gently.
   - A thin neon pink horizon line the sun rises above.
   - 3 orbital rings (conic-gradient arcs) rotating at different speeds
     in cyan, pink and purple — creates hypnotic asymmetric motion.
   - Outer sonar pulse via box-shadow rings. */
.waiting-synth {
  position: relative;
  width: 120px;
  height: 120px;
  margin-bottom: 1.1rem;
  border-radius: 50%;
  animation: synth-sonar 3s ease-out infinite;
}

/* Horizon line crossing the wrapper — the sun "rises" above it */
.synth-horizon {
  position: absolute;
  top: 58%;
  left: -8%;
  right: -8%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(var(--color-primary-rgb), 0.5) 20%,
    rgba(var(--color-primary-rgb), 1) 50%,
    rgba(var(--color-primary-rgb), 0.5) 80%,
    transparent 100%
  );
  box-shadow:
    0 0 10px rgba(var(--color-primary-rgb), 0.8),
    0 0 20px rgba(var(--color-primary-rgb), 0.4);
  pointer-events: none;
}

/* The synthwave sun: circle with gradient + horizontal band cut-outs */
.synth-sun {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 48px;
  height: 48px;
  margin: -24px 0 0 -24px;
  border-radius: 50%;
  background:
    /* Horizontal dark bands — the iconic "sun strip" look */
    repeating-linear-gradient(
      180deg,
      transparent 0px,
      transparent 4.5px,
      rgba(var(--color-bg-rgb), 0.95) 4.5px,
      rgba(var(--color-bg-rgb), 0.95) 6px
    ),
    /* The sun itself: yellow top → hot pink middle → purple bottom */
    linear-gradient(
        180deg,
        var(--color-warning) 0%,
        var(--color-sun-mid) 38%,
        var(--color-primary) 65%,
        var(--color-secondary) 100%
      );
  box-shadow:
    0 0 24px rgba(var(--color-primary-rgb), 0.6),
    0 0 48px rgba(var(--color-primary-rgb), 0.3),
    0 0 72px rgba(var(--color-secondary-rgb), 0.2);
  animation: sun-breathe 2.8s ease-in-out infinite;
}

/* Orbital rings — conic-gradient arcs masked to a ring shape */
.synth-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 50%;
  pointer-events: none;
}
.synth-ring-1 {
  width: 68px;
  height: 68px;
  margin: -34px 0 0 -34px;
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
  -webkit-mask: radial-gradient(circle, transparent 58%, #000 62%);
  mask: radial-gradient(circle, transparent 58%, #000 62%);
  filter: drop-shadow(0 0 5px var(--color-accent));
  animation: ring-cw 5s linear infinite;
}
.synth-ring-2 {
  width: 90px;
  height: 90px;
  margin: -45px 0 0 -45px;
  background: conic-gradient(
    from 90deg,
    transparent 0deg,
    var(--color-primary) 35deg,
    transparent 75deg,
    transparent 360deg
  );
  -webkit-mask: radial-gradient(circle, transparent 60%, #000 64%);
  mask: radial-gradient(circle, transparent 60%, #000 64%);
  filter: drop-shadow(0 0 6px var(--color-primary));
  animation: ring-ccw 8s linear infinite;
}
.synth-ring-3 {
  width: 114px;
  height: 114px;
  margin: -57px 0 0 -57px;
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
  -webkit-mask: radial-gradient(circle, transparent 62%, #000 66%);
  mask: radial-gradient(circle, transparent 62%, #000 66%);
  filter: drop-shadow(0 0 6px var(--color-secondary));
  animation: ring-cw 12s linear infinite;
}

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
    transform: scale(1.05);
    filter: brightness(1.12);
  }
}
@keyframes synth-sonar {
  0% {
    box-shadow:
      0 0 0 0 rgba(var(--color-primary-rgb), 0.35),
      0 0 0 0 rgba(var(--color-accent-rgb), 0.22);
  }
  80%,
  100% {
    box-shadow:
      0 0 0 34px rgba(var(--color-primary-rgb), 0),
      0 0 0 58px rgba(var(--color-accent-rgb), 0);
  }
}
.waiting-eyebrow {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 4px;
  color: var(--color-accent);
  text-transform: uppercase;
}
.waiting-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--color-text);
}
.waiting-sub {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

/* ===== Footer CTA ===== */
.lobby-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.5rem;
  padding-top: var(--space-md);
  z-index: 10;
  animation: rise-in 0.6s var(--ease-bounce) 0.5s both;
}
.btn-launch {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.9rem;
  width: 100%;
  padding: 1.1rem 1.8rem;
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 3px;
  background: linear-gradient(
    135deg,
    var(--color-primary) 0%,
    var(--color-secondary) 50%,
    var(--color-accent) 100%
  );
  background-size: 200% 100%;
  border: none;
  border-radius: var(--radius-full);
  cursor: pointer;
  box-shadow:
    0 10px 40px rgba(var(--color-primary-rgb), 0.4),
    0 0 0 1px rgba(var(--color-white-rgb), 0.1) inset;
  transition:
    transform 0.15s,
    box-shadow 0.2s,
    background-position 0.4s;
  overflow: hidden;
}
.btn-launch::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(var(--color-white-rgb), 0.25), transparent);
  transform: translateX(-100%);
  transition: transform 0.6s;
}
.btn-launch:hover:not(:disabled) {
  transform: translateY(-2px);
  background-position: 100% 0;
  box-shadow:
    0 15px 50px rgba(var(--color-primary-rgb), 0.55),
    0 0 0 1px rgba(var(--color-white-rgb), 0.2) inset;
}
.btn-launch:hover:not(:disabled)::before {
  transform: translateX(100%);
}
.btn-launch:active:not(:disabled) {
  transform: translateY(0);
}
.btn-launch:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
  filter: grayscale(0.3);
}
.launch-arrow {
  font-size: 0.85em;
  color: rgba(var(--color-white-rgb), 0.95);
}
.launch-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
  font-size: var(--text-sm);
  font-weight: 600;
  padding: 0.3rem 0.85rem;
  background: rgba(var(--color-black-rgb), 0.3);
  border: 1px solid rgba(var(--color-white-rgb), 0.12);
  border-radius: var(--radius-full);
  letter-spacing: 1px;
  text-transform: none;
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  white-space: nowrap;
}
.meta-emoji {
  font-size: 1.05em;
}
.meta-sep {
  opacity: 0.4;
  font-weight: 400;
}
.launch-hint {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 2px;
}

.error-banner {
  margin-top: var(--space-md);
  text-align: center;
  align-self: center;
}

/* ===== Entrance animations ===== */
@keyframes slam-in {
  0% {
    opacity: 0;
    transform: translateY(-20px) scale(0.97);
    filter: blur(8px);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
}
@keyframes rise-in {
  0% {
    opacity: 0;
    transform: translateY(24px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ===== Desktop layout =====
   Key fix for the scroll bug: the lobby is locked to 100vh so the PAGE
   never scrolls. If a panel's content is longer than its column, only
   that panel scrolls internally via overflow-y: auto with a thin scrollbar.
   No more 8rem dead space, no more accidental overflow. */
@media (min-width: 900px) {
  .lobby {
    /* Lock the dashboard to the viewport. No page scroll, ever. */
    height: 100vh;
    min-height: 0;
    overflow: hidden;
  }
  .lobby-header {
    grid-template-columns: 1fr auto;
    align-items: end;
  }
  .header-chips {
    justify-content: flex-end;
  }
  /* Grid consumes the space between header and footer */
  .lobby-grid {
    flex: 1 1 auto;
    min-height: 0;
  }
  /* Panels scroll internally if their content overflows the column */
  .panel {
    max-height: 100%;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(var(--color-white-rgb), 0.15) transparent;
  }
  .panel::-webkit-scrollbar {
    width: 6px;
  }
  .panel::-webkit-scrollbar-thumb {
    background: rgba(var(--color-white-rgb), 0.15);
    border-radius: 3px;
  }
  /* Footer sits at the bottom of the flex column, inline (not sticky) */
  .lobby-footer {
    position: static;
    flex: 0 0 auto;
    padding-top: 0;
  }
  .btn-launch {
    max-width: 520px;
    margin: 0 auto;
  }
}

/* ===== Tablet/mobile layout (<900px): stack + fixed footer bar ===== */
@media (max-width: 899px) {
  .lobby {
    /* Leave room for the fixed launch bar so the last content isn't hidden */
    padding-bottom: 6.5rem;
  }
  .lobby-footer {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 20;
    padding: 0.75rem clamp(1rem, 4vw, 1.5rem) calc(0.75rem + env(safe-area-inset-bottom));
    background: linear-gradient(180deg, transparent 0%, rgba(var(--color-bg-rgb), 0.95) 45%);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
  }
  .btn-launch {
    /* Thumb-friendly touch target — WCAG 2.5.5 level AAA recommends 44×44 */
    min-height: 52px;
    padding: 0.9rem 1.4rem;
  }
}

/* ===== Mobile polish (small screens) ===== */
@media (max-width: 560px) {
  .lobby {
    gap: 0.8rem;
    padding-left: 1rem;
    padding-right: 1rem;
  }
  .marquee-code {
    font-size: clamp(2.6rem, 13vw, 4rem);
  }
  .panel {
    padding: 0.9rem 1rem;
  }
  .mode-grid {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }
  .mode-card {
    flex-direction: row;
    align-items: center;
    gap: 0.85rem;
    padding: 0.75rem 0.95rem;
    min-height: 56px;
  }
  .mode-card .mode-tag {
    margin-left: auto;
    text-align: right;
  }
  .mode-emoji {
    font-size: 1.7rem;
  }
  /* Chips: horizontal scroll instead of wrap so they don't eat vertical space */
  .header-chips {
    flex-wrap: nowrap;
    overflow-x: auto;
    margin: 0 calc(-1 * var(--space-md));
    padding: 0 var(--space-md);
    scrollbar-width: none;
  }
  .header-chips::-webkit-scrollbar {
    display: none;
  }
  .chip {
    flex-shrink: 0;
    min-height: 40px;
    padding: 0.6rem 1rem;
  }
  .seg {
    min-height: 40px;
    padding: 0.5rem 1rem;
  }
}

/* ===== Reduced motion ===== */
@media (prefers-reduced-motion: reduce) {
  .bg-orb,
  .pulse-dot,
  .marquee-cursor,
  .waiting-synth,
  .synth-sun,
  .synth-ring,
  .btn-launch::before,
  .panel,
  .lobby-header,
  .lobby-footer {
    animation: none !important;
  }
}
</style>
