/* eslint-disable security/detect-object-injection -- test uses controlled event keys */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// In-memory mock of a socket.io-client Socket — records events + handlers so
// tests can assert what the composable emitted and trigger server-like events.
type Handler = (...args: unknown[]) => void

interface FakeSocket {
  connected: boolean
  auth: { token: string }
  on: ReturnType<typeof vi.fn>
  off: ReturnType<typeof vi.fn>
  emit: ReturnType<typeof vi.fn>
  disconnect: ReturnType<typeof vi.fn>
  handlers: Record<string, Handler[]>
  __fire: (event: string, ...args: unknown[]) => void
}

const createFakeSocket = (auth: { token: string }): FakeSocket => {
  const socket: FakeSocket = {
    connected: false,
    auth,
    handlers: {},
    on: vi.fn((event: string, handler: Handler) => {
      ;(socket.handlers[event] ??= []).push(handler)
    }),
    off: vi.fn((event: string, handler?: Handler) => {
      if (!handler) {
        delete socket.handlers[event]
      } else {
        socket.handlers[event] = (socket.handlers[event] ?? []).filter((h) => h !== handler)
      }
    }),
    emit: vi.fn(),
    disconnect: vi.fn(() => {
      socket.connected = false
    }),
    __fire(event: string, ...args: unknown[]) {
      for (const h of socket.handlers[event] ?? []) h(...args)
    },
  }
  return socket
}

const ioMock = vi.fn()
vi.mock('socket.io-client', () => ({
  io: (...args: unknown[]) => ioMock(...args),
}))

async function freshUseSocket() {
  // Re-import the module so the module-level `socket` singleton is reset
  // between tests, otherwise state leaks across it blocks.
  vi.resetModules()
  const mod = await import('../../src/composables/useSocket')
  return mod.useSocket()
}

describe('useSocket', () => {
  let latestSocket: FakeSocket | null = null

  beforeEach(() => {
    latestSocket = null
    ioMock.mockReset()
    ioMock.mockImplementation((opts: { auth: { token: string } }) => {
      latestSocket = createFakeSocket(opts.auth)
      return latestSocket
    })
  })

  it('connect() calls io() with the given token and wires connect/disconnect handlers', async () => {
    const { connect, connected } = await freshUseSocket()
    const s = connect('tkn-abc')
    expect(ioMock).toHaveBeenCalledOnce()
    const callArg = ioMock.mock.calls[0][0] as { auth: { token: string } }
    expect(callArg.auth.token).toBe('tkn-abc')
    expect(s).toBe(latestSocket)
    // Composable should have registered internal connect/disconnect listeners
    expect(latestSocket!.handlers.connect).toHaveLength(1)
    expect(latestSocket!.handlers.disconnect).toHaveLength(1)

    // Firing 'connect' flips the reactive state
    latestSocket!.__fire('connect')
    expect(connected.value).toBe(true)
    latestSocket!.__fire('disconnect')
    expect(connected.value).toBe(false)
  })

  it('connect() returns the existing socket if already connected (idempotent)', async () => {
    const { connect } = await freshUseSocket()
    const first = connect('t1')
    latestSocket!.connected = true
    const second = connect('t2')
    expect(second).toBe(first)
    // io() must NOT have been called a second time
    expect(ioMock).toHaveBeenCalledOnce()
  })

  it('emit/on/off proxy to the underlying socket', async () => {
    const { connect, emit, on, off } = await freshUseSocket()
    connect('t')
    const handler = vi.fn()

    on('room_updated', handler)
    expect(latestSocket!.on).toHaveBeenCalledWith('room_updated', handler)

    emit('join_room', { code: 'ABC' })
    expect(latestSocket!.emit).toHaveBeenCalledWith('join_room', { code: 'ABC' })

    off('room_updated', handler)
    expect(latestSocket!.off).toHaveBeenCalledWith('room_updated', handler)
  })

  it('emit/on/off are silent no-ops before connect()', async () => {
    const { emit, on, off } = await freshUseSocket()
    // No socket yet — must not throw
    expect(() => emit('x', {})).not.toThrow()
    expect(() => on('x', () => {})).not.toThrow()
    expect(() => off('x', () => {})).not.toThrow()
  })

  it('disconnect() tears down the socket and flips connected to false', async () => {
    const { connect, disconnect, connected, getSocket } = await freshUseSocket()
    connect('t')
    latestSocket!.connected = true
    // Simulate the real 'connect' event so connected ref is true
    latestSocket!.__fire('connect')
    expect(connected.value).toBe(true)

    disconnect()
    expect(latestSocket!.disconnect).toHaveBeenCalled()
    expect(connected.value).toBe(false)
    expect(getSocket()).toBeNull()
  })

  it('getSocket() returns the current socket or null', async () => {
    const { connect, getSocket } = await freshUseSocket()
    expect(getSocket()).toBeNull()
    connect('t')
    expect(getSocket()).toBe(latestSocket)
  })
})
