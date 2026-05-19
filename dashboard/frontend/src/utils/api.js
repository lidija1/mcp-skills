const post = (url, body) =>
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async r => {
    const data = await r.json()
    if (!r.ok) {
      throw new Error(data.detail || data.error || `Request failed with HTTP ${r.status}`)
    }
    return data
  })

export const api = {
  // ── Health ────────────────────────────────────────────────────────────
  health: () => fetch('/api/health').then(r => r.json()),

  // ── Jobs ──────────────────────────────────────────────────────────────
  listJobs: () => fetch('/api/jobs').then(r => r.json()),
  getJob: id => fetch(`/api/jobs/${id}`).then(r => r.json()),
  explorerPrompt: prompt => post('/api/explorer/prompt', { prompt }),
  explorerRun: prompt => post('/api/explorer/run', { prompt }),

  // ── Policy ────────────────────────────────────────────────────────────
  getArchetypes: (lob = '') => fetch(`/api/policy/archetypes?lob=${lob}`).then(r => r.json()),
  createPersona: (lob, description) => post('/api/policy/create-persona', { lob, description }),
  runFlow: (lob, persona_json) => post('/api/policy/run-flow', { lob, persona_json }),
  quickRun: (lob, description) => post('/api/policy/quick-run', { lob, description }),
  batchRun: scenarios => post('/api/policy/batch-run', { scenarios }),

  // ── UW ────────────────────────────────────────────────────────────────
  listRules: (lob = '') => fetch(`/api/uw/rules?lob=${lob}`).then(r => r.json()),
  runAudit: lob => post('/api/uw/audit', { lob }),
  runRuleCases: (lob, rule_id) => post('/api/uw/rule-cases', { lob, rule_id }),
  runCustomBoundary: (lob, description, expected_outcome, expected_conditions) =>
    post('/api/uw/custom-boundary', { lob, description, expected_outcome, expected_conditions }),
  runFullAudit: () => post('/api/uw/full-audit', {}),

  // ── Chat ──────────────────────────────────────────────────────────────
  chatGreeting: () => fetch('/api/chat/greeting').then(r => r.json()),
  chat: (message, confirmedTool = null, confirmedParams = null) =>
    post('/api/chat/message', {
      message,
      confirmed_tool: confirmedTool,
      confirmed_params: confirmedParams,
    }),
}
