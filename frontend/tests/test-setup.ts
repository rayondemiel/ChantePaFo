// Global test setup: stubs browser APIs jsdom doesn't implement so
// components that touch matchMedia/clipboard can be mounted freely.

// Plain function (no vi.fn) so the mock is always a real callable
// regardless of when vitest initialises its mock runtime.
function makeMediaQueryList(query: string) {
  return {
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => true,
  }
}

// Assign via Object.defineProperty so jsdom's read-only descriptor is replaced.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: makeMediaQueryList as unknown as typeof window.matchMedia,
})

// Expose as a simple function property too, in case some code reads it
// from `globalThis` before the window descriptor is picked up.
;(globalThis as unknown as { matchMedia: typeof window.matchMedia }).matchMedia =
  makeMediaQueryList as unknown as typeof window.matchMedia

// Minimal clipboard stub — overridden in individual tests that need spies.
if (!('clipboard' in navigator)) {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: async () => {} },
    writable: true,
    configurable: true,
  })
}
