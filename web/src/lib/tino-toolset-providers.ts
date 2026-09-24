import type { ToolsetProvider } from "@/lib/api";

/** Tino does not offer the upstream Nous subscription/account flow. */
export function filterTinoToolsetProviders(providers: ToolsetProvider[]): ToolsetProvider[] {
  return providers.filter((provider) => !provider.requires_nous_auth);
}
