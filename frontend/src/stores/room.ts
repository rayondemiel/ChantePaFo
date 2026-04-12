import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RoomState } from '../types'
import { useAuthStore } from './auth'

export const useRoomStore = defineStore('room', () => {
  const room = ref<RoomState | null>(null)

  const isHost = computed(() => {
    const auth = useAuthStore()
    if (!room.value || !auth.userId) return false
    return room.value.players.some((p) => p.is_host && p.id === auth.userId)
  })

  function setRoom(data: RoomState) {
    room.value = data
  }

  function clearRoom() {
    room.value = null
  }

  return { room, isHost, setRoom, clearRoom }
})
