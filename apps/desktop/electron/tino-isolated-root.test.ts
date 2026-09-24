import assert from 'node:assert/strict'
import path from 'node:path'

import { test } from 'vitest'

import { resolveTinoIsolatedRoot, TINO_ISOLATED_ROOT_CONFIG } from './tino-isolated-root'

const source = '/work/tino-agent'
const colocatedResources = path.join(
  source, 'apps/desktop/release/mac-arm64/Tino Agent.app/Contents/Resources'
)
const externalRelease = '/private/tino-build/release'
const externalResources = path.join(
  externalRelease, 'mac-arm64/Tino Agent.app/Contents/Resources'
)

function checkoutPaths(root: string): string[] {
  return [
    path.join(root, 'hermes_cli/main.py'),
    path.join(root, '.venv/bin/python'),
    path.join(root, '.tino-runtime/home')
  ]
}

test('a bundle still inside its checkout uses that private runtime first', () => {
  const known = new Set(checkoutPaths(source))
  const root = resolveTinoIsolatedRoot(
    colocatedResources,
    candidate => known.has(candidate),
    () => { throw new Error('external marker must not be read') }
  )

  assert.equal(root, source)
})

test('a signed external bundle recovers its checkout from the adjacent release marker', () => {
  const known = new Set(checkoutPaths(source))
  const expectedMarker = path.join(externalRelease, TINO_ISOLATED_ROOT_CONFIG)
  const root = resolveTinoIsolatedRoot(
    externalResources,
    candidate => known.has(candidate),
    candidate => {
      assert.equal(candidate, expectedMarker)
      return JSON.stringify({ root: source })
    }
  )

  assert.equal(root, source)
})

test('an invalid marker never selects another agent home', () => {
  for (const marker of ['not JSON', JSON.stringify({ root: '../relative' }), JSON.stringify({ root: '/missing' })]) {
    const root = resolveTinoIsolatedRoot(externalResources, () => false, () => marker)

    assert.equal(root, null)
  }
})
