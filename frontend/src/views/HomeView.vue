<template>
  <div class="home" :class="{ 'home--mobile': isMobile, 'home--desktop': !isMobile }">
    <div class="home-bg-orb home-bg-orb-1" aria-hidden="true"></div>
    <div class="home-bg-orb home-bg-orb-2" aria-hidden="true"></div>

    <header class="home-hero">
      <span class="home-eyebrow">// MUSIC PARTY</span>
      <h1 class="text-display text-gradient home-title">ChantePaFo</h1>
      <p class="tagline">Jeux musicaux entre potes · 2 à 10 joueurs</p>
    </header>

    <div class="actions">
      <section class="section section-create">
        <span class="section-eyebrow">// CRÉER</span>
        <h2 class="section-title">Nouvelle room</h2>
        <input
          ref="hostInput"
          v-model="hostName"
          class="input-text"
          placeholder="Ton pseudo"
          maxlength="32"
          @keydown.enter="createRoom"
        />
        <button class="btn btn-primary" :disabled="!hostName.trim() || loading" @click="createRoom">
          Créer une room
        </button>
      </section>

      <div class="divider" aria-hidden="true"></div>

      <section class="section section-join">
        <span class="section-eyebrow">// REJOINDRE</span>
        <h2 class="section-title">Code existant</h2>
        <input
          v-model="joinCode"
          class="input-text input-code"
          placeholder="FUNK4242"
          maxlength="8"
          @keydown.enter="joinRoom"
        />
        <input
          v-model="joinName"
          class="input-text"
          placeholder="Ton pseudo"
          maxlength="32"
          @keydown.enter="joinRoom"
        />
        <button
          class="btn btn-secondary"
          :disabled="!joinCode.trim() || !joinName.trim() || loading"
          @click="joinRoom"
        >
          Rejoindre
        </button>
      </section>
    </div>

    <p v-if="error" class="feedback feedback-wrong home-error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useSocket } from '../composables/useSocket'
import { useBreakpoint } from '../composables/useBreakpoint'

const router = useRouter()
const authStore = useAuthStore()
const roomStore = useRoomStore()
const { connect, emit: socketEmit } = useSocket()
const { isMobile } = useBreakpoint()

const PSEUDO_STORAGE_KEY = 'chantepafo.pseudo'

const hostInput = ref<HTMLInputElement | null>(null)
const savedPseudo =
  typeof localStorage === 'undefined' ? '' : (localStorage.getItem(PSEUDO_STORAGE_KEY) ?? '')
const hostName = ref(savedPseudo)
const joinCode = ref('')
const joinName = ref(savedPseudo)
const error = ref('')
const loading = ref(false)

function persistPseudo(value: string) {
  const trimmed = value.trim()
  if (trimmed) localStorage.setItem(PSEUDO_STORAGE_KEY, trimmed)
}

watch(hostName, persistPseudo)
watch(joinName, persistPseudo)

onMounted(() => {
  hostInput.value?.focus()
})

async function ensureAuth(name: string): Promise<boolean> {
  if (authStore.isLoggedIn) return true
  // Auto-register: generate a safe username (no spaces/accents) from the display name.
  // The display name (host_name/player_name) keeps the user's original input.
  const safeUsername =
    name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9_.-]/g, '_')
      .replace(/_+/g, '_')
      .slice(0, 20) + `_${Date.now()}`
  const email = `${safeUsername}@chantepafo.app`
  const password = crypto.randomUUID()
  const resp = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: safeUsername, email, password }),
  })
  if (!resp.ok) {
    error.value = await extractError(resp, "Erreur d'inscription")
    return false
  }
  authStore.setAuth(await resp.json())
  return true
}

async function extractError(resp: Response, fallback: string): Promise<string> {
  try {
    const body = await resp.json()
    if (body.detail) {
      if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        // FastAPI validation error — extract the human-readable message
        const msg: string = body.detail[0].msg
        return msg.replace(/^Value error, /, '')
      }
      if (typeof body.detail === 'string') {
        return body.detail
      }
    }
  } catch {
    // response wasn't JSON
  }
  return fallback
}

async function createRoom() {
  if (!hostName.value.trim()) return
  loading.value = true
  error.value = ''

  if (!(await ensureAuth(hostName.value.trim()))) {
    loading.value = false
    return
  }

  const resp = await authStore.authFetch('/api/rooms', {
    method: 'POST',
    body: JSON.stringify({ host_name: hostName.value.trim() }),
  })

  if (!resp.ok) {
    error.value = await extractError(resp, 'Erreur création room')
    loading.value = false
    return
  }

  const data = await resp.json()
  roomStore.setRoom(data.room)
  connect(authStore.token!)
  socketEmit('join_room', { code: data.room.code })
  router.push(`/${data.room.code}`)
}

async function joinRoom() {
  if (!joinCode.value.trim() || !joinName.value.trim()) return
  loading.value = true
  error.value = ''

  if (!(await ensureAuth(joinName.value.trim()))) {
    loading.value = false
    return
  }

  const code = joinCode.value.trim().toUpperCase()
  const resp = await authStore.authFetch(`/api/rooms/${code}/join`, {
    method: 'POST',
    body: JSON.stringify({ player_name: joinName.value.trim() }),
  })

  if (!resp.ok) {
    error.value = await extractError(resp, 'Room introuvable ou pleine')
    loading.value = false
    return
  }

  const data = await resp.json()
  roomStore.setRoom(data.room)
  connect(authStore.token!)
  socketEmit('join_room', { code })
  router.push(`/${code}`)
}
</script>

<style scoped>
/* =========================================
   HOME — NEON ENTRY
   =========================================
   Desktop: full-screen with hero + side-by-side create/join
   Mobile:  compact vertical stack with thumb-friendly CTAs
   ========================================= */

.home {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  width: 100%;
  padding: clamp(1.5rem, 4vw, 3rem) clamp(1rem, 4vw, 3rem);
  gap: clamp(1.5rem, 3vw, 3rem);
  isolation: isolate;
  overflow: hidden;
}

/* Ambient background orbs — same family as lobby for consistency */
.home-bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.45;
  mix-blend-mode: screen;
  pointer-events: none;
  z-index: -1;
}
.home-bg-orb-1 {
  top: -120px;
  left: -80px;
  width: 480px;
  height: 480px;
  background: radial-gradient(circle, var(--color-primary) 0%, transparent 65%);
  animation: home-drift 22s ease-in-out infinite;
}
.home-bg-orb-2 {
  bottom: -160px;
  right: -120px;
  width: 520px;
  height: 520px;
  background: radial-gradient(circle, var(--color-accent) 0%, transparent 65%);
  animation: home-drift 26s ease-in-out infinite reverse;
}
@keyframes home-drift {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(50px, -40px) scale(1.1);
  }
}

/* ===== Hero band ===== */
.home-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  text-align: center;
  animation: hero-rise 0.8s var(--ease-bounce) both;
}
.home-eyebrow {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 5px;
  color: var(--color-accent);
  text-transform: uppercase;
  opacity: 0.75;
}
.home-title {
  font-size: clamp(3.2rem, 10vw, 6.5rem);
  line-height: 0.95;
  letter-spacing: 0.03em;
  filter: drop-shadow(0 0 32px rgba(var(--color-primary-rgb), 0.3))
    drop-shadow(0 0 60px rgba(var(--color-accent-rgb), 0.2));
}
.tagline {
  color: var(--color-text-muted);
  font-size: var(--text-lg);
  letter-spacing: 1px;
}

/* ===== Actions: sections stacked (mobile) or side-by-side (desktop) ===== */
.actions {
  display: flex;
  flex-direction: column;
  gap: clamp(1rem, 2vw, 2rem);
  width: 100%;
  max-width: 440px;
  margin: 0 auto;
  align-items: stretch;
  animation: sections-rise 0.8s var(--ease-bounce) 0.25s both;
}
.section {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: clamp(1.2rem, 2.5vw, 1.8rem);
  background: linear-gradient(
    160deg,
    rgba(var(--color-surface-rgb), 0.75),
    rgba(var(--color-surface-rgb), 0.45)
  );
  border: 1px solid rgba(var(--color-white-rgb), 0.08);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow:
    0 20px 60px rgba(var(--color-black-rgb), 0.4),
    inset 0 1px 0 rgba(var(--color-white-rgb), 0.05);
}
.section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    135deg,
    rgba(var(--color-accent-rgb), 0.3),
    transparent 40%,
    transparent 60%,
    rgba(var(--color-primary-rgb), 0.3)
  );
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
.section-eyebrow {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 3px;
  color: var(--color-accent);
  text-transform: uppercase;
  opacity: 0.75;
}
.section-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--color-text);
  margin: 0 0 0.3rem;
}
.home-error {
  align-self: center;
  text-align: center;
}

/* ===== Desktop: full-screen, hero + two columns side-by-side ===== */
@media (min-width: 900px) {
  .home {
    justify-content: center;
    padding: clamp(2rem, 4vw, 4rem) clamp(2rem, 5vw, 5rem);
    gap: clamp(2rem, 3vw, 3.5rem);
  }
  .actions {
    flex-direction: row;
    max-width: 900px;
    align-items: stretch;
    gap: 0;
    position: relative;
  }
  .section {
    flex: 1;
  }
  .divider {
    position: relative;
    width: 1px;
    height: auto;
    margin: 0 clamp(1rem, 2vw, 2rem);
    background: linear-gradient(
      180deg,
      transparent,
      var(--color-primary),
      var(--color-accent),
      transparent
    );
    opacity: 0.4;
  }
  .divider::after {
    content: 'OU';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: var(--color-bg);
    padding: 0.3rem 0.6rem;
    font-family: var(--font-display);
    font-size: var(--text-xs);
    letter-spacing: 3px;
    color: var(--color-text-muted);
    border-radius: var(--radius-full);
    border: 1px solid var(--color-border);
  }
}

/* ===== Mobile: thumb-friendly, compact vertical stack ===== */
@media (max-width: 899px) {
  .home {
    justify-content: flex-start;
    padding-top: clamp(2rem, 8vw, 4rem);
    padding-bottom: clamp(1.5rem, 5vw, 3rem);
  }
  .home-title {
    font-size: clamp(3rem, 14vw, 4.5rem);
  }
  .tagline {
    font-size: var(--text-base);
  }
  .divider {
    height: 1px;
    width: 60%;
    margin: 0 auto;
    background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
    opacity: 0.3;
  }
  .section {
    /* Bigger touch targets on phones */
    padding: 1.1rem 1.2rem;
  }
  .section .btn {
    padding: 0.9rem 1.5rem;
    font-size: var(--text-base);
    min-height: 48px; /* WCAG touch target */
  }
  .section .input-text {
    padding: 0.85rem 1rem;
    min-height: 48px;
    font-size: var(--text-base);
  }
}

/* ===== Entrance animations ===== */
@keyframes hero-rise {
  0% {
    opacity: 0;
    transform: translateY(-16px);
    filter: blur(8px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}
@keyframes sections-rise {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-bg-orb,
  .home-hero,
  .actions {
    animation: none !important;
  }
}
</style>
