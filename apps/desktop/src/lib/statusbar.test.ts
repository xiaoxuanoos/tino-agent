import { describe, expect, it } from 'vitest'

import { cacheHitLabel, sessionPerformanceLabel, tokensPerSecondLabel } from '@/lib/statusbar'

const base = { calls: 0, input: 0, output: 0, total: 0 }

describe('statusbar usage readouts', () => {
  it('paints the backend cache-hit and throughput fields, and stays blank when they are absent', () => {
    // The backend omits both fields (rather than sending 0) when it has no data
    // — a provider with no cache reads, or a session before its first call.
    expect(cacheHitLabel(base)).toBe('')
    expect(tokensPerSecondLabel(base)).toBe('')

    expect(cacheHitLabel({ ...base, cache_hit_pct: 87 })).toBe('87%')
    expect(tokensPerSecondLabel({ ...base, avg_tps: 41.6 })).toBe('42 t/s')
  })

  it('summarizes only measured session metrics in Chinese', () => {
    expect(sessionPerformanceLabel(base, true)).toBe('')
    expect(sessionPerformanceLabel({
      ...base,
      calls: 17,
      input: 59_000,
      output: 163_000,
      avg_tps: 277,
      avg_latency_s: 2.1,
      cache_hit_pct: 99.7
    }, true)).toBe('模型 17 次 · 平均 2.1 秒/次 · 277 tok/s · 缓存 99.7% · 输入 59k tok · 输出 163k tok')
  })
})
