import { compactNumber } from '@hermes/shared'
import { useState } from 'react'

import { StableText } from '@/components/chat/stable-text'
import { useViewedInterval } from '@/hooks/use-viewed-interval'
import type { UsageStats } from '@/types/hermes'

export function formatDuration(elapsedMs: number): string {
  const totalSeconds = Math.max(0, Math.floor(elapsedMs / 1000))
  const seconds = totalSeconds % 60
  const minutes = Math.floor(totalSeconds / 60) % 60
  const hours = Math.floor(totalSeconds / 3600)
  const ss = String(seconds).padStart(2, '0')
  const mm = String(minutes).padStart(2, '0')

  return hours > 0 ? `${hours}:${mm}:${ss}` : `${minutes}:${ss}`
}

export function compactPath(path: string, max = 44): string {
  const trimmed = path.trim()

  if (trimmed.length <= max) {
    return trimmed
  }

  const segments = trimmed.split('/').filter(Boolean)

  if (segments.length < 2) {
    return `…${trimmed.slice(-(max - 1))}`
  }

  const tail = segments.slice(-2).join('/')

  return tail.length + 2 >= max ? `…${tail.slice(-(max - 1))}` : `…/${tail}`
}

export function contextBar(percent: number | undefined, width = 10): string {
  const bounded = Math.max(0, Math.min(100, percent ?? 0))
  const filled = Math.round((bounded / 100) * width)

  return `${'█'.repeat(filled)}${'░'.repeat(width - filled)}`
}

export function usageContextLabel(usage: UsageStats): string {
  if (usage.context_max) {
    return `${usage.context_estimated ? '~' : ''}${compactNumber(usage.context_used ?? 0)}/${compactNumber(usage.context_max)}`
  }

  return usage.total > 0 ? `${compactNumber(usage.total)} tok` : ''
}

export function contextBarLabel(usage: UsageStats): string {
  if (!usage.context_max) {
    return ''
  }

  const pct = Math.max(0, Math.min(100, Math.round(usage.context_percent ?? 0)))

  return `[${contextBar(usage.context_percent)}] ${usage.context_estimated ? '~' : ''}${pct}%`
}

/** `87%` for a reported hit rate; '' when the backend omitted it (no cache
 *  reads yet, or a provider that doesn't report them). The backend already
 *  clamps and rounds, so this only guards a malformed/absent field. */
export function cacheHitLabel(usage: UsageStats): string {
  const pct = usage.cache_hit_pct

  return typeof pct === 'number' && Number.isFinite(pct) ? `${Number(pct.toFixed(1))}%` : ''
}

/** `42 t/s` for the rolling throughput; '' before the first completed call. */
export function tokensPerSecondLabel(usage: UsageStats): string {
  const tps = usage.avg_tps

  return typeof tps === 'number' && Number.isFinite(tps) && tps > 0 ? `${Math.round(tps)} t/s` : ''
}

/** Compact, truthful session summary. Rounds, tool time and first-token
 * latency are deliberately omitted: the gateway does not report them yet. */
export function sessionPerformanceLabel(usage: UsageStats, chinese = false): string {
  if (!usage.calls) {
    return ''
  }

  const parts = chinese
    ? [`模型 ${usage.calls} 次`]
    : [`${usage.calls} model calls`]
  const tps = tokensPerSecondLabel(usage)
  const cache = cacheHitLabel(usage)

  if (typeof usage.avg_latency_s === 'number' && Number.isFinite(usage.avg_latency_s) && usage.avg_latency_s > 0) {
    parts.push(chinese ? `平均 ${usage.avg_latency_s.toFixed(1)} 秒/次` : `${usage.avg_latency_s.toFixed(1)} s/call`)
  }
  if (tps) {
    parts.push(tps.replace(' t/s', ' tok/s'))
  }
  if (cache) {
    parts.push(chinese ? `缓存 ${cache}` : `cache ${cache}`)
  }
  parts.push(chinese ? `输入 ${compactNumber(usage.input)} tok` : `in ${compactNumber(usage.input)} tok`)
  parts.push(chinese ? `输出 ${compactNumber(usage.output)} tok` : `out ${compactNumber(usage.output)} tok`)

  return parts.join(' · ')
}

export function LiveDuration({ since }: { since: number | null | undefined }) {
  const [now, setNow] = useState(() => Date.now())

  useViewedInterval(() => setNow(Date.now()), 1000, Boolean(since))

  if (!since) {
    return null
  }

  return <StableText>{formatDuration(now - since)}</StableText>
}
