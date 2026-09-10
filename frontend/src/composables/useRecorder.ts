import { ref, readonly } from 'vue'
import { useAuthStore } from '../stores/auth'

const DEFAULT_MAX_DURATION_MS = 30_000
const TICK_MS = 100

// Backend allows audio/webm and audio/mp4 (Safari fallback). Pick the first
// supported variant — order matters: webm/opus is preferred for size+quality.
function pickMimeType(): { mimeType: string; extension: string } {
  if (typeof MediaRecorder === 'undefined') {
    return { mimeType: 'audio/webm', extension: 'webm' }
  }
  if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
    return { mimeType: 'audio/webm;codecs=opus', extension: 'webm' }
  }
  if (MediaRecorder.isTypeSupported('audio/webm')) {
    return { mimeType: 'audio/webm', extension: 'webm' }
  }
  // Safari path
  return { mimeType: 'audio/mp4', extension: 'mp4' }
}

async function sha256Hex(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer()
  const digest = await crypto.subtle.digest('SHA-256', buffer)
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

export interface UploadResult {
  url: string
  sha256: string
}

export function useRecorder() {
  const isRecording = ref(false)
  const isUploading = ref(false)
  const audioBlob = ref<Blob | null>(null)
  const audioUrl = ref<string | null>(null)
  const elapsedMs = ref(0)
  const error = ref<string | null>(null)

  let mediaRecorder: MediaRecorder | null = null
  let mediaStream: MediaStream | null = null
  let chunks: Blob[] = []
  let timer: ReturnType<typeof setInterval> | null = null
  let mimeInfo = pickMimeType()
  let stopResolve: (() => void) | null = null

  function clearTimer(): void {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  function releaseStream(): void {
    if (mediaStream) {
      for (const track of mediaStream.getTracks()) track.stop()
      mediaStream = null
    }
  }

  function revokeAudioUrl(): void {
    if (audioUrl.value) {
      URL.revokeObjectURL(audioUrl.value)
      audioUrl.value = null
    }
  }

  async function startRecording(maxDurationMs = DEFAULT_MAX_DURATION_MS): Promise<void> {
    if (isRecording.value) return
    error.value = null
    revokeAudioUrl()
    audioBlob.value = null
    elapsedMs.value = 0

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'mic_access_denied'
      throw e
    }

    mimeInfo = pickMimeType()
    try {
      mediaRecorder = new MediaRecorder(mediaStream, { mimeType: mimeInfo.mimeType })
    } catch {
      // Browser rejected our preferred mime → fall back to defaults.
      mediaRecorder = new MediaRecorder(mediaStream)
    }

    chunks = []
    mediaRecorder.ondataavailable = (e: BlobEvent) => {
      if (e.data && e.data.size > 0) chunks.push(e.data)
    }
    mediaRecorder.onstop = () => {
      // Use the actual chunk type when available — Safari sometimes returns
      // a slightly different mime than what we requested.
      const type = chunks[0]?.type || mimeInfo.mimeType
      const blob = new Blob(chunks, { type })
      audioBlob.value = blob
      audioUrl.value = URL.createObjectURL(blob)
      clearTimer()
      releaseStream()
      isRecording.value = false
      stopResolve?.()
      stopResolve = null
    }

    mediaRecorder.start()
    isRecording.value = true

    const startedAt = Date.now()
    timer = setInterval(() => {
      elapsedMs.value = Date.now() - startedAt
      if (elapsedMs.value >= maxDurationMs && isRecording.value) {
        stopRecording()
      }
    }, TICK_MS)
  }

  function stopRecording(): Promise<void> {
    if (!isRecording.value || !mediaRecorder) return Promise.resolve()
    return new Promise((resolve) => {
      stopResolve = resolve
      try {
        mediaRecorder?.stop()
      } catch {
        // Already stopped — release manually.
        clearTimer()
        releaseStream()
        isRecording.value = false
        resolve()
      }
    })
  }

  async function uploadRecording(): Promise<UploadResult | null> {
    if (!audioBlob.value) return null
    const auth = useAuthStore()
    const token = auth.token
    if (!token) {
      error.value = 'not_authenticated'
      return null
    }

    isUploading.value = true
    try {
      const hash = await sha256Hex(audioBlob.value)
      const formData = new FormData()
      formData.append('file', audioBlob.value, `recording.${mimeInfo.extension}`)

      const resp = await fetch('/api/audio/upload', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'X-Content-SHA256': hash,
        },
        body: formData,
      })

      if (!resp.ok) {
        error.value = `upload_failed_${resp.status}`
        return null
      }
      const data = (await resp.json()) as UploadResult
      // Round-trip integrity check — server returns the hash it computed.
      if (data.sha256 && data.sha256 !== hash) {
        error.value = 'sha256_roundtrip_mismatch'
        return null
      }
      return data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'upload_error'
      return null
    } finally {
      isUploading.value = false
    }
  }

  function reset(): void {
    revokeAudioUrl()
    audioBlob.value = null
    elapsedMs.value = 0
    error.value = null
    chunks = []
  }

  function cancel(): void {
    clearTimer()
    releaseStream()
    if (mediaRecorder && isRecording.value) {
      try {
        mediaRecorder.stop()
      } catch {
        // ignore
      }
    }
    isRecording.value = false
    reset()
  }

  return {
    isRecording: readonly(isRecording),
    isUploading: readonly(isUploading),
    audioBlob: readonly(audioBlob),
    audioUrl: readonly(audioUrl),
    elapsedMs: readonly(elapsedMs),
    error: readonly(error),
    startRecording,
    stopRecording,
    uploadRecording,
    reset,
    cancel,
  }
}
