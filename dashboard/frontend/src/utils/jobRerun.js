/** Infer policy execution kind from type, tool name, or job label. */
export function inferExecutionType(job) {
  const explicit = job?.execution_type
  if (explicit === 'quick_run' || explicit === 'policy_flow' || explicit === 'create_persona') return explicit

  if (explicit === 'chat_execution') {
    const tool = job?.metadata?.tool
    if (tool === 'run_quick_policy') return 'quick_run'
    if (tool === 'create_persona') return 'create_persona'
  }

  const label = (job?.label || '').toLowerCase()
  if (label.includes('quick policy')) return 'quick_run'
  if (label.includes('policy journey')) return 'policy_flow'
  if (label.includes('build profile')) return 'create_persona'

  return explicit || ''
}

function extractSourceDescription(result) {
  if (!result || typeof result !== 'string') return ''
  const match = result.match(/\*\*Source Description:\*\*\s*(.+?)(?:\n\n|\n```|$)/is)
  return match?.[1]?.trim() || ''
}

function quickRunDescription(job) {
  const metadata = job?.metadata || {}
  const payload = metadata.rerun_payload || {}
  const params = metadata.params || {}

  return (
    payload.description ||
    metadata.description ||
    params.description ||
    extractSourceDescription(job?.result)
  )
}

function policyFlowPersona(job) {
  const metadata = job?.metadata || {}
  const payload = metadata.rerun_payload || {}
  const params = metadata.params || {}

  const persona = payload.persona_json ?? metadata.persona_json ?? params.persona_json
  if (persona == null || persona === '') return null
  return persona
}

function personaDescription(job) {
  const metadata = job?.metadata || {}
  const params = metadata.params || {}

  return (
    metadata.description ||
    params.description ||
    extractSourceDescription(job?.result)
  )
}

/** Whether the backend /api/jobs/:id/rerun endpoint can handle this job. */
export function canRerunJob(job) {
  if (!job) return false

  const type = inferExecutionType(job)
  if (type === 'quick_run') return Boolean(quickRunDescription(job))
  if (type === 'policy_flow') return policyFlowPersona(job) != null
  if (type === 'create_persona') return Boolean(personaDescription(job))

  return false
}

function isPolicyAutomationLabel(job) {
  const label = (job?.label || '').toLowerCase()
  return (
    label.includes('quick policy') ||
    label.includes('policy journey') ||
    label.includes('policy test') ||
    label.includes('personal auto') ||
    label.includes('personal-auto')
  )
}

function hasPolicyLob(job) {
  const metadata = job?.metadata || {}
  const candidates = [
    metadata.lob,
    metadata.requested_lob,
    metadata.params?.lob,
    metadata.rerun_payload?.lob,
  ]

  return candidates.some(value => {
    const lob = String(value || '').toLowerCase().trim()
    return (
      lob === 'homeowner' ||
      lob === 'personal-auto' ||
      lob === 'personal auto' ||
      lob === 'auto'
    )
  })
}

/** Show Run again in the UI for canceled policy automation jobs. */
export function shouldShowRerunAction(job) {
  if (!job || job.status !== 'canceled') return false
  if (canRerunJob(job)) return true
  return isPolicyAutomationLabel(job) || hasPolicyLob(job)
}
