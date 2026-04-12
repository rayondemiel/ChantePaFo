<template>
  <div class="home">
    <h1 class="text-display text-gradient home-title">ChantePaFo</h1>
    <p class="tagline">Jeux musicaux entre potes</p>

    <div class="actions">
      <div class="section">
        <input
          v-model="hostName"
          class="input-text"
          placeholder="Ton pseudo"
          maxlength="32"
          @keydown.enter="createRoom"
        />
        <button class="btn btn-primary" :disabled="!hostName.trim() || loading" @click="createRoom">
          Créer une room
        </button>
      </div>

      <div class="divider"></div>

      <div class="section">
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
      </div>
    </div>

    <p v-if="error" class="feedback feedback-wrong">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useSocket } from '../composables/useSocket'

const router = useRouter()
const authStore = useAuthStore()
const roomStore = useRoomStore()
const { connect, emit: socketEmit } = useSocket()

const hostName = ref('')
const joinCode = ref('')
const joinName = ref('')
const error = ref('')
const loading = ref(false)

async function ensureAuth(name: string): Promise<boolean> {
  if (authStore.isLoggedIn) return true
  // Auto-register with a random email for party simplicity
  const email = `${name.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}@chantepafo.local`
  const password = crypto.randomUUID()
  const resp = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: name.trim(), email, password }),
  })
  if (!resp.ok) {
    error.value = "Erreur d'inscription"
    return false
  }
  authStore.setAuth(await resp.json())
  return true
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
    error.value = 'Erreur création room'
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
    error.value = 'Room introuvable ou pleine'
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
.home {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-xl);
  gap: var(--space-lg);
  min-height: 100vh;
  justify-content: center;
}
.home-title {
  font-size: var(--text-hero);
}
.tagline {
  color: var(--color-text-muted);
  font-size: var(--text-base);
}
.actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  width: 100%;
  max-width: 400px;
}
.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
  opacity: 0.3;
}
</style>
