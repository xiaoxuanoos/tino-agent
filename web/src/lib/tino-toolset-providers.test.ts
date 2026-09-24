import { describe, expect, it } from "vitest";
import type { ToolsetProvider } from "@/lib/api";
import { filterTinoToolsetProviders } from "./tino-toolset-providers";

const provider = (name: string, requires_nous_auth: boolean): ToolsetProvider => ({
  name,
  badge: "",
  tag: "",
  env_vars: [],
  post_setup: null,
  requires_nous_auth,
  is_active: false,
});

describe("Tino toolset provider choices", () => {
  it("removes upstream-account choices without hiding direct API providers", () => {
    const direct = provider("API key", false);
    const upstream = provider("Upstream account", true);
    expect(filterTinoToolsetProviders([upstream, direct])).toEqual([direct]);
    expect(filterTinoToolsetProviders([upstream])).toEqual([]);
  });
});
