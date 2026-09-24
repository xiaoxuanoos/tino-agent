import path from 'node:path'

export const TINO_ISOLATED_ROOT_CONFIG = '.tino-checkout.json'

/** Find the Tino checkout without ever falling through to another agent's home. */
export function resolveTinoIsolatedRoot(
  resourcesPath: string,
  exists: (candidate: string) => boolean,
  readText: (candidate: string) => string
): string | null {
  const valid = (root: string): boolean =>
    exists(path.join(root, 'hermes_cli', 'main.py')) &&
    exists(path.join(root, '.venv', 'bin', 'python')) &&
    exists(path.join(root, '.tino-runtime', 'home'))

  const colocated = path.resolve(resourcesPath, '../../../../../../../')

  if (valid(colocated)) return colocated

  // A File Provider checkout can make macOS add FinderInfo to an app bundle,
  // breaking code signing. The app may therefore live in an isolated local
  // release directory while source and user data stay in the checkout. The
  // marker is beside mac-arm64/, outside the signed .app and never published.
  const config = path.resolve(resourcesPath, '../../../../', TINO_ISOLATED_ROOT_CONFIG)

  try {
    const parsed: unknown = JSON.parse(readText(config))
    const configured = (parsed as { root?: unknown } | null)?.root

    if (typeof configured === 'string' && path.isAbsolute(configured)) {
      const root = path.resolve(configured)

      if (valid(root)) return root
    }
  } catch {
    // Missing, unreadable, or malformed local config: use normal bootstrap.
  }

  return null
}
