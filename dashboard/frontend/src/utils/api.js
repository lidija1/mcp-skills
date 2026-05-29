const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')

  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {}
}

const post = async (url, body) => {
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Request failed')
  }

  return data
}

const get = async url => {
  const response = await fetch(url, {
    credentials: 'include',
    headers: getAuthHeaders(),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Request failed')
  }

  return data
}

const del = async url => {
  const response = await fetch(url, {
    method: 'DELETE',
    credentials: 'include',
    headers: getAuthHeaders(),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Request failed')
  }

  return data
}

const policyLobForApi = lob => {
  const value = String(lob || '').toLowerCase().trim()
  if (value === 'personal-auto' || value === 'personal_auto' || value === 'personal auto') {
    return 'auto'
  }
  return value
}

export const api = {
  // ── Health ────────────────────────────────────────────────────────────
  health: () => get('/api/health'),

  // ── Jobs ──────────────────────────────────────────────────────────────
  listJobs: () => get('/api/jobs'),
  getJob: id => get(`/api/jobs/${id}`),
  explorerPrompt: prompt => post('/api/explorer/prompt', { prompt }),
  explorerRun: prompt => post('/api/explorer/run', { prompt }),

  // ── Policy ────────────────────────────────────────────────────────────
  getArchetypes: (lob = '') => get(`/api/policy/archetypes?lob=${policyLobForApi(lob)}`),
  createPersona: (lob, description) => post('/api/policy/create-persona', { lob: policyLobForApi(lob), description }),
  runFlow: (lob, persona_json) => post('/api/policy/run-flow', { lob: policyLobForApi(lob), persona_json }),
  quickRun: (lob, description) => post('/api/policy/quick-run', { lob: policyLobForApi(lob), description }),
  batchRun: scenarios => post('/api/policy/batch-run', { scenarios }),
  runApiPlainAssertion: prompt => post('/api/api-tests/plain-assert', { prompt }),
  runApiSuite: (prompts, suite_name, shared_persona_prompt = null) => post('/api/api-tests/suite', { prompts, suite_name, shared_persona_prompt }),
  smartVariations: (builder, count) => post('/api/api-tests/smart-variations', { builder, count }),

  // ── Saved Suites ──────────────────────────────────────────────────────────
  getSuites: () => get('/api/suites'),
  saveSuite: (name, prompts, builder, sharedPersona) =>
    post('/api/suites', { name, prompts, builder, shared_persona: sharedPersona }),
  deleteSuite: id => del(`/api/suites/${id}`),

  // ── UW ────────────────────────────────────────────────────────────────
  listRules: (lob = '') => get(`/api/uw/rules?lob=${lob}`),
  runAudit: lob => post('/api/uw/audit', { lob }),
  runRuleCases: (lob, rule_id) => post('/api/uw/rule-cases', { lob, rule_id }),
  runCustomBoundary: (lob, description, expected_outcome, expected_conditions) =>
    post('/api/uw/custom-boundary', { lob, description, expected_outcome, expected_conditions }),
  runFullAudit: () => post('/api/uw/full-audit', {}),

  // ── Chat ──────────────────────────────────────────────────────────────
  chatGreeting: () => get('/api/chat/greeting'),
  chat: (message, confirmedTool = null, confirmedParams = null) =>
    post('/api/chat/message', {
      message,
      confirmed_tool: confirmedTool,
      confirmed_params: confirmedParams,
    }),
  chatAsk: message => post('/api/chat/ask', { message }),

  // ── Auth ──────────────────────────────────────────────────────────────
login: (username, password) =>
  post('/api/login', {
    username,
    password,
  }),

register: (first_name, last_name, username, password) =>
  post('/api/register', {
    first_name,
    last_name,
    username,
    password,
  }),

me: () => get('/api/auth/me'),

logout: () => post('/api/auth/logout', {}),
}
