import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../../src/stores/auth'

// MediaRecorder isn't implemented in jsdom — install a controllable fake
// before each test so the composable's start/stop cycle can run end-to-end.

interface FakeRecorderHandle {
  instance: FakeRecorder | null
}

class FakeRecorder {
  state: 'inactive' | 'recording' | 'stopped' = 'inactive'
  mimeType: string
  ondataavailable: ((e: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  constructor(_stream: MediaStream, opts?: { mimeType?: string }) {
    this.mimeType = opts?.mimeType ?? 'audio/webm'
  }
  start(): void {
    this.state = 'recording'
  }
  stop(): void {
    this.state = 'stopped'
    this.ondataavailable?.({ data: new Blob(['abc'], { type: this.mimeType }) })
    this.onstop?.()
  }
  static isTypeSupported(type: string): boolean {
    return type.startsWith('audio/webm')
  }
}

function installFakeRecorder(): FakeRecorderHandle {
  const handle: FakeRecorderHandle = { instance: null }
  class Tracked extends FakeRecorder {
    constructor(stream: MediaStream, opts?: { mimeType?: string }) {
      super(stream, opts)
      handle.instance = this
    }
  }
  ;(globalThis as unknown as { MediaRecorder: typeof FakeRecorder }).MediaRecorder =
    Tracked as unknown as typeof FakeRecorder
  return handle
}

function installFakeMediaDevices(stopCalls: { count: number }): void {
  const tracks = [
    {
      stop: () => {
        stopCalls.count += 1
      },
    },
  ]
  const stream = { getTracks: () => tracks } as unknown as MediaStream
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
    writable: true,
    configurable: true,
  })
}

function installBlobArrayBuffer(): void {
  // jsdom's Blob lacks arrayBuffer() in older versions — polyfill via FileReader
  // is overkill; just slice the underlying string parts we put in.
  if (typeof Blob.prototype.arrayBuffer !== 'function') {
    Object.defineProperty(Blob.prototype, 'arrayBuffer', {
      configurable: true,
      value: function (this: Blob) {
        return Promise.resolve(new ArrayBuffer(this.size))
      },
    })
  }
}

function installCryptoSubtle(): void {
  if (!('subtle' in crypto)) {
    Object.defineProperty(crypto, 'subtle', {
      value: {
        digest: async (_alg: string, data: ArrayBuffer) => {
          // Deterministic 32-byte "hash" derived from the input length so we
          // can assert the upload header is filled correctly without pulling
          // in a real SHA-256 implementation.
          const out = new Uint8Array(32)
          out[0] = data.byteLength & 0xff
          return out.buffer
        },
      },
      configurable: true,
    })
  }
}

async function freshUseRecorder() {
  vi.resetModules()
  const mod = await import('../../src/composables/useRecorder')
  return mod.useRecorder()
}

describe('useRecorder', () => {
  let stopCalls: { count: number }
  let recorderHandle: FakeRecorderHandle

  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    stopCalls = { count: 0 }
    recorderHandle = installFakeRecorder()
    installFakeMediaDevices(stopCalls)
    installBlobArrayBuffer()
    installCryptoSubtle()
    // URL.createObjectURL doesn't exist in jsdom by default.
    if (typeof URL.createObjectURL !== 'function') {
      URL.createObjectURL = vi.fn(() => 'blob:fake')
      URL.revokeObjectURL = vi.fn()
    }
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('transitions to recording state on start and back on stop', async () => {
    const r = await freshUseRecorder()
    expect(r.isRecording.value).toBe(false)
    await r.startRecording(60_000)
    expect(r.isRecording.value).toBe(true)
    await r.stopRecording()
    expect(r.isRecording.value).toBe(false)
    expect(r.audioBlob.value).not.toBeNull()
    expect(r.audioUrl.value).toBe('blob:fake')
  })

  it('releases the mic stream when recording stops', async () => {
    const r = await freshUseRecorder()
    await r.startRecording(60_000)
    await r.stopRecording()
    expect(stopCalls.count).toBe(1)
  })

  it('uploadRecording sends Bearer + X-Content-SHA256 header with FormData', async () => {
    const r = await freshUseRecorder()
    const auth = useAuthStore()
    auth.setAuth({ token: 'tok-abc', username: 'alice', user_id: 'u1' })

    await r.startRecording(60_000)
    await r.stopRecording()

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          url: '/uploads/x.webm',
          sha256: '0300000000000000000000000000000000000000000000000000000000000000',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )

    const result = await r.uploadRecording()
    expect(result?.url).toBe('/uploads/x.webm')
    expect(fetchSpy).toHaveBeenCalledOnce()
    const [url, init] = fetchSpy.mock.calls[0]
    expect(url).toBe('/api/audio/upload')
    const headers = init?.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer tok-abc')
    expect(headers['X-Content-SHA256']).toMatch(/^[0-9a-f]{64}$/)
    expect(init?.body).toBeInstanceOf(FormData)
  })

  it('uploadRecording returns null and sets error when not authenticated', async () => {
    const r = await freshUseRecorder()
    await r.startRecording(60_000)
    await r.stopRecording()
    const result = await r.uploadRecording()
    expect(result).toBeNull()
    expect(r.error.value).toBe('not_authenticated')
  })

  it('uploadRecording returns null and sets error on a 4xx response', async () => {
    const r = await freshUseRecorder()
    const auth = useAuthStore()
    auth.setAuth({ token: 'tok', username: 'alice', user_id: 'u1' })

    await r.startRecording(60_000)
    await r.stopRecording()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('nope', { status: 400 }))

    const result = await r.uploadRecording()
    expect(result).toBeNull()
    expect(r.error.value).toBe('upload_failed_400')
  })

  it('uploadRecording flags a server hash mismatch as a round-trip failure', async () => {
    const r = await freshUseRecorder()
    const auth = useAuthStore()
    auth.setAuth({ token: 'tok', username: 'alice', user_id: 'u1' })

    await r.startRecording(60_000)
    await r.stopRecording()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ url: '/uploads/x.webm', sha256: 'deadbeef' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const result = await r.uploadRecording()
    expect(result).toBeNull()
    expect(r.error.value).toBe('sha256_roundtrip_mismatch')
  })

  it('uploadRecording returns null when no recording exists', async () => {
    const r = await freshUseRecorder()
    const result = await r.uploadRecording()
    expect(result).toBeNull()
  })

  it('reset clears the audio blob and resets elapsed/error', async () => {
    const r = await freshUseRecorder()
    await r.startRecording(60_000)
    await r.stopRecording()
    expect(r.audioBlob.value).not.toBeNull()
    r.reset()
    expect(r.audioBlob.value).toBeNull()
    expect(r.audioUrl.value).toBeNull()
    expect(r.elapsedMs.value).toBe(0)
    expect(r.error.value).toBeNull()
  })

  it('startRecording surfaces a getUserMedia rejection via the error ref', async () => {
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn().mockRejectedValue(new Error('denied')) },
      writable: true,
      configurable: true,
    })
    const r = await freshUseRecorder()
    await expect(r.startRecording(60_000)).rejects.toThrow('denied')
    expect(r.isRecording.value).toBe(false)
    expect(r.error.value).toBe('denied')
  })

  it('cancel stops the recorder and releases the stream', async () => {
    const r = await freshUseRecorder()
    await r.startRecording(60_000)
    expect(r.isRecording.value).toBe(true)
    r.cancel()
    expect(r.isRecording.value).toBe(false)
    expect(stopCalls.count).toBe(1)
    // Sanity: recorder was actually stopped from the cancel path.
    expect(recorderHandle.instance?.state).toBe('stopped')
  })
})
