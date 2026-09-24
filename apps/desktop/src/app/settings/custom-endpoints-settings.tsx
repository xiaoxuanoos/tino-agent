import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { SegmentedControl } from '@/components/ui/segmented-control'
import {
  activateCustomEndpoint,
  deleteCustomEndpoint,
  getCustomEndpoints,
  saveCustomEndpoint,
  validateCustomEndpoint
} from '@/hermes'
import { type Locale, useI18n } from '@/i18n'
import { triggerHaptic } from '@/lib/haptics'
import { Check, Globe, Loader2, Plus, Save, Trash2, Zap } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { confirm } from '@/store/confirm'
import { notify, notifyError } from '@/store/notifications'
import type {
  CustomEndpoint,
  CustomEndpointApiMode,
  CustomEndpointModelDetail,
  CustomEndpointUpdate
} from '@/types/hermes'

import { EmptyState, Pill, SectionHeading, SettingsContent, SettingsSkeleton } from './primitives'
import { ActiveProfileNote } from './profile-scope'

interface CustomEndpointsSettingsProps {
  onConfigSaved?: () => void
  onMainModelChanged?: (provider: string, model: string) => void
}

interface EndpointForm {
  apiKey: string
  apiMode: CustomEndpointApiMode
  baseUrl: string
  contextLength: string
  discoverModels: boolean
  id: string
  makeDefault: boolean
  model: string
  name: string
}

const EN_ENDPOINT_COPY = {
  active: 'Active',
  activationFailed: 'Activation failed',
  addEndpoint: 'Add Endpoint',
  apiKey: 'API Key',
  apiKeySet: 'API key set',
  apiMode: 'API Mode',
  autoDetect: 'Auto-detect',
  chatCompletions: 'Chat Completions',
  context: 'Context',
  defaultModel: 'Default Model',
  deleteConfirm: (name: string) => `Delete ${name}?`,
  deleteFailed: 'Delete failed',
  discoverModels: 'Discover models',
  editEndpoint: 'Edit Endpoint',
  endpointReachable: 'Endpoint is reachable.',
  endpointReachableVia: (transport: string) => `Endpoint is reachable (${transport} route served).`,
  endpointValidationFailed: 'Endpoint validation failed.',
  endpointUrl: 'Endpoint URL',
  keepCurrentKey: 'Leave blank to keep current key',
  loadFailed: 'Could not load custom endpoints',
  modelsFound: (count: number) => `Found ${count} models.`,
  name: 'Name',
  newEndpoint: 'New endpoint',
  optional: 'Optional',
  providerId: 'Provider ID',
  responsesApi: 'Responses API',
  save: 'Save',
  saveFailed: 'Save failed',
  saved: 'Custom endpoint saved.',
  test: 'Test',
  use: 'Use',
  useForNewChats: 'Use for new chats',
  validationFailed: 'Validation failed'
}

const ZH_ENDPOINT_COPY: typeof EN_ENDPOINT_COPY = {
  active: '当前使用',
  activationFailed: '启用模型服务商失败',
  addEndpoint: '添加模型服务商',
  apiKey: 'API 密钥',
  apiKeySet: '已设置 API 密钥',
  apiMode: 'API 协议',
  autoDetect: '自动检测',
  chatCompletions: 'Chat Completions',
  context: '上下文长度',
  defaultModel: '默认模型',
  deleteConfirm: name => `删除「${name}」？`,
  deleteFailed: '删除模型服务商失败',
  discoverModels: '自动发现模型',
  editEndpoint: '编辑模型服务商',
  endpointReachable: '接口连接成功。',
  endpointReachableVia: transport => `接口连接成功（已验证 ${transport}）。`,
  endpointValidationFailed: '接口连接测试失败。',
  endpointUrl: '接口地址',
  keepCurrentKey: '留空则保留现有密钥',
  loadFailed: '无法加载模型服务商',
  modelsFound: count => `发现 ${count} 个模型。`,
  name: '服务商名称',
  newEndpoint: '新建服务商',
  optional: '选填',
  providerId: '服务商 ID',
  responsesApi: 'Responses API',
  save: '保存',
  saveFailed: '保存失败',
  saved: '模型服务商已保存。',
  test: '测试连接',
  use: '使用',
  useForNewChats: '用于新对话',
  validationFailed: '连接测试失败'
}

function endpointCopy(locale: Locale) {
  return locale === 'zh' || locale === 'zh-hant' ? ZH_ENDPOINT_COPY : EN_ENDPOINT_COPY
}

const EMPTY_FORM: EndpointForm = {
  apiKey: '',
  apiMode: '',
  baseUrl: '',
  contextLength: '',
  discoverModels: true,
  id: '',
  makeDefault: true,
  model: '',
  name: ''
}

function formFromEndpoint(endpoint: CustomEndpoint): EndpointForm {
  return {
    apiKey: '',
    apiMode: endpoint.api_mode ?? '',
    baseUrl: endpoint.base_url,
    contextLength: endpoint.context_length ? String(endpoint.context_length) : '',
    discoverModels: endpoint.discover_models,
    id: endpoint.id,
    makeDefault: Boolean(endpoint.is_current),
    model: endpoint.model,
    name: endpoint.name
  }
}

function toPayload(
  form: EndpointForm,
  models?: string[],
  modelDetails?: CustomEndpointModelDetail[]
): CustomEndpointUpdate {
  const contextLength = Number.parseInt(form.contextLength, 10)

  return {
    id: form.id.trim() || undefined,
    name: form.name.trim(),
    base_url: form.baseUrl.trim(),
    model: form.model.trim(),
    api_key: form.apiKey.trim() || undefined,
    api_mode: form.apiMode,
    context_length: Number.isFinite(contextLength) && contextLength > 0 ? contextLength : undefined,
    discover_models: form.discoverModels,
    make_default: form.makeDefault,
    models: models?.length ? models : undefined,
    model_details: modelDetails?.length ? modelDetails : undefined
  }
}

export function CustomEndpointsSettings({ onConfigSaved, onMainModelChanged }: CustomEndpointsSettingsProps) {
  const { locale, t } = useI18n()
  const copy = endpointCopy(locale)
  // Same choices as `hermes model`'s custom-provider setup; '' = runtime auto-detect.
  const apiModeOptions: readonly { id: CustomEndpointApiMode; label: string }[] = [
    { id: '', label: copy.autoDetect },
    { id: 'chat_completions', label: copy.chatCompletions },
    { id: 'codex_responses', label: copy.responsesApi },
    { id: 'anthropic_messages', label: 'Anthropic Messages' }
  ]
  const mounted = useRef(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [activating, setActivating] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [endpoints, setEndpoints] = useState<CustomEndpoint[]>([])
  const [form, setForm] = useState<EndpointForm>(EMPTY_FORM)
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([])
  // Alias metadata from the last Test; the backend resolves a picked alias to its
  // canonical model + reasoning effort on Save (#93622).
  const [discoveredDetails, setDiscoveredDetails] = useState<CustomEndpointModelDetail[]>([])

  async function refresh() {
    const data = await getCustomEndpoints()

    if (mounted.current) {
      setEndpoints(data.endpoints)
    }
  }

  // eslint-disable-next-line no-restricted-syntax -- lifecycle guard drops stale async completions; it does not mirror an atom
  useEffect(() => {
    let cancelled = false
    mounted.current = true

    async function load() {
      try {
        const data = await getCustomEndpoints()

        if (cancelled) {
          return
        }

        setEndpoints(data.endpoints)
        const current = data.endpoints.find(endpoint => endpoint.is_current) ?? data.endpoints[0]

        if (current) {
          setForm(formFromEndpoint(current))
          setDiscoveredModels(current.models)
        }
      } catch (err) {
        notifyError(err, copy.loadFailed)
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
      mounted.current = false
    }
  }, [])

  async function handleSave() {
    try {
      setSaving(true)
      const response = await saveCustomEndpoint(toPayload(form, discoveredModels, discoveredDetails))

      if (!mounted.current) {
        return
      }

      setEndpoints(response.endpoints)
      const saved = response.endpoints.find(endpoint => endpoint.id === response.id)

      if (saved) {
        setForm(formFromEndpoint(saved))
        setDiscoveredModels(saved.models)
      }

      if (saved && saved.is_current) {
        onMainModelChanged?.(saved.id, saved.model)
      }

      triggerHaptic('success')
      onConfigSaved?.()
      notify({ kind: 'success', message: copy.saved })
    } catch (err) {
      if (mounted.current) {
        notifyError(err, copy.saveFailed)
      }
    } finally {
      if (mounted.current) {
        setSaving(false)
      }
    }
  }

  async function handleValidate() {
    try {
      setTesting(true)
      const response = await validateCustomEndpoint(toPayload(form))

      if (!mounted.current) {
        return
      }

      setDiscoveredModels(response.models)
      setDiscoveredDetails(response.model_details ?? [])

      if (response.ok) {
        // Persist the URL that actually served /models (e.g. "<root>/v1" when the user typed the
        // bare root): chat POSTs {base_url}/chat/completions verbatim, so saving the typed root
        // would 404 every request even though the test looked green (#65488).
        const resolvedBaseUrl = response.resolved_base_url?.trim()

        if (!form.model && response.models[0]) {
          setForm(current => ({ ...current, model: response.models[0] }))
        }

        if (resolvedBaseUrl && resolvedBaseUrl !== form.baseUrl.trim().replace(/\/+$/, '')) {
          setForm(current => ({ ...current, baseUrl: resolvedBaseUrl }))
        }

        // The backend also POSTed the transport the runtime will use; name it so an
        // auto-detected mode is visible before Save (#93622).
        const transport = apiModeOptions.find(option => option.id === response.transport_checked)?.label
        const reachable = transport ? copy.endpointReachableVia(transport) : copy.endpointReachable
        notify({
          kind: 'success',
          message: response.models.length ? `${reachable} ${copy.modelsFound(response.models.length)}` : reachable
        })
      } else {
        notify({
          kind: response.reachable ? 'warning' : 'error',
          message: response.message || copy.endpointValidationFailed
        })
      }
    } catch (err) {
      if (mounted.current) {
        notifyError(err, copy.validationFailed)
      }
    } finally {
      if (mounted.current) {
        setTesting(false)
      }
    }
  }

  async function handleActivate(endpoint: CustomEndpoint) {
    try {
      setActivating(endpoint.id)
      const response = await activateCustomEndpoint(endpoint.id)

      if (!mounted.current) {
        return
      }

      await refresh()

      if (!mounted.current) {
        return
      }

      onConfigSaved?.()
      onMainModelChanged?.(response.provider, response.model)
      triggerHaptic('success')
    } catch (err) {
      if (mounted.current) {
        notifyError(err, copy.activationFailed)
      }
    } finally {
      if (mounted.current) {
        setActivating(null)
      }
    }
  }

  async function handleDelete(endpoint: CustomEndpoint) {
    if (!(await confirm({ destructive: true, title: copy.deleteConfirm(endpoint.name) }))) {
      return
    }

    try {
      setDeleting(endpoint.id)
      const response = await deleteCustomEndpoint(endpoint.id)

      if (!mounted.current) {
        return
      }

      setEndpoints(response.endpoints)

      if (form.id === endpoint.id) {
        setForm(EMPTY_FORM)
        setDiscoveredModels([])
        setDiscoveredDetails([])
      }

      onConfigSaved?.()
      triggerHaptic('success')
    } catch (err) {
      if (mounted.current) {
        notifyError(err, copy.deleteFailed)
      }
    } finally {
      if (mounted.current) {
        setDeleting(null)
      }
    }
  }

  if (loading) {
    return <SettingsSkeleton sections={[{ heading: true, rows: 3 }]} />
  }

  const allModelOptions = Array.from(new Set([...discoveredModels, form.model].filter(Boolean)))
  const canSave = form.name.trim() && form.baseUrl.trim() && form.model.trim()

  return (
    <SettingsContent>
      <ActiveProfileNote className="mb-5" />
      <div className="space-y-6">
        <section>
          <SectionHeading icon={Globe} meta={`${endpoints.length}`} page title={t.settings.customEndpoints.title} />
          <div className="mb-3 rounded-md border border-primary/20 bg-primary/[0.04] px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
            {t.settings.customEndpoints.introDescription}
          </div>
          <div className="divide-y divide-border/40 rounded-md border border-border/50">
            {endpoints.length ? (
              endpoints.map(endpoint => (
                <div className="grid gap-3 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center" key={endpoint.id}>
                  <button
                    className="min-w-0 text-left"
                    onClick={() => {
                      setForm(formFromEndpoint(endpoint))
                      setDiscoveredModels(endpoint.models)
                      setDiscoveredDetails([])
                    }}
                    type="button"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="truncate text-sm font-medium">{endpoint.name}</span>
                      {endpoint.is_current && (
                        <Pill tone="primary">
                          <Check className="size-3" />
                          {copy.active}
                        </Pill>
                      )}
                      {endpoint.source === 'direct-config' && <Pill>config.yaml</Pill>}
                    </div>
                    <div className="mt-1 truncate font-mono text-[0.7rem] text-muted-foreground">
                      {endpoint.base_url}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      <span>{endpoint.model}</span>
                      {endpoint.has_api_key && <span>{endpoint.api_key_preview ?? copy.apiKeySet}</span>}
                    </div>
                  </button>
                  <div className="flex items-center gap-2 sm:justify-end">
                    <Button
                      disabled={endpoint.is_current || activating === endpoint.id}
                      onClick={() => void handleActivate(endpoint)}
                      size="sm"
                      variant="outline"
                    >
                      {activating === endpoint.id ? <Loader2 className="animate-spin" /> : <Zap />}
                      {copy.use}
                    </Button>
                    {endpoint.source !== 'direct-config' && (
                      <Button
                        aria-label={t.settings.customEndpoints.deleteEndpoint}
                        className="hover:text-destructive"
                        disabled={deleting === endpoint.id}
                        onClick={() => void handleDelete(endpoint)}
                        size="icon-sm"
                        variant="ghost"
                      >
                        {deleting === endpoint.id ? <Loader2 className="animate-spin" /> : <Trash2 />}
                      </Button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <EmptyState
                description={t.settings.customEndpoints.emptyDescription}
                title={t.settings.customEndpoints.emptyTitle}
              />
            )}
          </div>
        </section>

        <section>
          <SectionHeading icon={Plus} title={form.id ? copy.editEndpoint : copy.addEndpoint} />
          <div className="grid gap-3 rounded-md border border-border/50 p-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1.5 text-xs text-muted-foreground">
                {copy.name}
                <Input
                  onChange={event => setForm(current => ({ ...current, name: event.target.value }))}
                  placeholder={t.settings.customEndpoints.namePlaceholder}
                  value={form.name}
                />
              </label>
              <label className="grid gap-1.5 text-xs text-muted-foreground">
                {copy.providerId}
                <Input
                  onChange={event => setForm(current => ({ ...current, id: event.target.value }))}
                  placeholder="axet-proxy"
                  value={form.id}
                />
              </label>
            </div>
            <label className="grid gap-1.5 text-xs text-muted-foreground">
              {copy.endpointUrl}
              <Input
                onChange={event => setForm(current => ({ ...current, baseUrl: event.target.value }))}
                placeholder="http://127.0.0.1:8081/v1"
                value={form.baseUrl}
              />
            </label>
            <fieldset className="grid min-w-0 gap-1.5 text-xs text-muted-foreground">
              <legend className="mb-1.5">{copy.apiMode}</legend>
              <SegmentedControl
                className="w-full max-w-full"
                onChange={apiMode => setForm(current => ({ ...current, apiMode }))}
                options={apiModeOptions}
                value={form.apiMode}
              />
            </fieldset>
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem]">
              <label className="grid gap-1.5 text-xs text-muted-foreground">
                {copy.defaultModel}
                <Input
                  list="custom-endpoint-models"
                  onChange={event => setForm(current => ({ ...current, model: event.target.value }))}
                  placeholder="gpt-5.4"
                  value={form.model}
                />
                <datalist id="custom-endpoint-models">
                  {allModelOptions.map(model => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              </label>
              <label className="grid gap-1.5 text-xs text-muted-foreground">
                {copy.context}
                <Input
                  inputMode="numeric"
                  onChange={event => setForm(current => ({ ...current, contextLength: event.target.value }))}
                  placeholder={t.settings.customEndpoints.contextPlaceholder}
                  value={form.contextLength}
                />
              </label>
            </div>
            <label className="grid gap-1.5 text-xs text-muted-foreground">
              {copy.apiKey}
              <Input
                onChange={event => setForm(current => ({ ...current, apiKey: event.target.value }))}
                placeholder={form.id ? copy.keepCurrentKey : copy.optional}
                type="password"
                value={form.apiKey}
              />
            </label>
            <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
              <label className="flex items-center gap-2">
                <Checkbox
                  checked={form.makeDefault}
                  onCheckedChange={checked => setForm(current => ({ ...current, makeDefault: checked === true }))}
                />
                {copy.useForNewChats}
              </label>
              <label className="flex items-center gap-2">
                <Checkbox
                  checked={form.discoverModels}
                  onCheckedChange={checked => setForm(current => ({ ...current, discoverModels: checked === true }))}
                />
                {copy.discoverModels}
              </label>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={testing || !form.baseUrl.trim()}
                onClick={() => void handleValidate()}
                variant="outline"
              >
                {testing ? <Loader2 className="animate-spin" /> : <Zap />}
                {copy.test}
              </Button>
              <Button disabled={saving || !canSave} onClick={() => void handleSave()}>
                {saving ? <Loader2 className="animate-spin" /> : <Save />}
                {copy.save}
              </Button>
              <Button
                className={cn(!form.id && 'hidden')}
                onClick={() => {
                  setForm(EMPTY_FORM)
                  setDiscoveredModels([])
                  setDiscoveredDetails([])
                }}
                type="button"
                variant="ghost"
              >
                {copy.newEndpoint}
              </Button>
            </div>
          </div>
        </section>
      </div>
    </SettingsContent>
  )
}
