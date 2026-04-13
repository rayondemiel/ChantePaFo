import {
  ref,
  onMounted,
  onUnmounted,
  readonly,
  inject,
  provide,
  type InjectionKey,
  type Ref,
  type DeepReadonly,
} from 'vue'

/**
 * Single-source-of-truth viewport breakpoint.
 *
 * Architecture:
 * - `provideBreakpoint()` is called ONCE at the root (App.vue). It sets up
 *   a single matchMedia listener and provides the reactive ref via inject key.
 * - `useBreakpoint()` in any descendant simply injects that ref — no extra
 *   listeners, no redundant state.
 * - If no ancestor has provided (e.g. in isolated unit tests), `useBreakpoint()`
 *   gracefully falls back to creating its own local listener.
 */

type BreakpointState = DeepReadonly<Ref<boolean>>

const BreakpointKey: InjectionKey<BreakpointState> = Symbol('ChantePaFo:isMobile')

const DEFAULT_QUERY = '(max-width: 899px)'

/** Internal: create a reactive ref that follows a matchMedia query. */
function createBreakpointRef(query: string): BreakpointState {
  const isMobile = ref(false)
  let mql: MediaQueryList | null = null

  function sync() {
    if (mql) isMobile.value = mql.matches
  }

  onMounted(() => {
    if (typeof globalThis === 'undefined' || !globalThis.matchMedia) return
    mql = globalThis.matchMedia(query)
    sync()
    mql.addEventListener('change', sync)
  })

  onUnmounted(() => {
    if (mql) mql.removeEventListener('change', sync)
  })

  return readonly(isMobile)
}

/**
 * Call ONCE in App.vue to install the app-wide breakpoint state.
 * All descendants can then `useBreakpoint()` and inject the same ref.
 */
export function provideBreakpoint(query = DEFAULT_QUERY) {
  const isMobile = createBreakpointRef(query)
  provide(BreakpointKey, isMobile)
  return { isMobile }
}

/**
 * Consume the app-wide breakpoint state.
 * Falls back to a local listener if no ancestor has `provideBreakpoint`d
 * (useful for unit tests and isolated previews).
 */
export function useBreakpoint(query = DEFAULT_QUERY) {
  const injected = inject(BreakpointKey, null)
  if (injected) return { isMobile: injected }
  return { isMobile: createBreakpointRef(query) }
}
