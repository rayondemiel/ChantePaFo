import { io, Socket } from 'socket.io-client'
import { ref, readonly } from 'vue'

let socket: Socket | null = null
const connected = ref(false)

export function useSocket() {
  function connect(token: string) {
    if (socket?.connected) return socket
    socket = io({
      auth: { token },
      transports: ['websocket', 'polling'],
    })
    socket.on('connect', () => {
      connected.value = true
    })
    socket.on('disconnect', () => {
      connected.value = false
    })
    return socket
  }

  function getSocket(): Socket | null {
    return socket
  }

  function emit(event: string, data: Record<string, unknown>) {
    socket?.emit(event, data)
  }

  function on(event: string, handler: (...args: unknown[]) => void) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    socket?.on(event, handler as any)
  }

  function off(event: string, handler?: (...args: unknown[]) => void) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    socket?.off(event, handler as any)
  }

  function disconnect() {
    socket?.disconnect()
    socket = null
    connected.value = false
  }

  return { connect, emit, on, off, disconnect, connected: readonly(connected), getSocket }
}
