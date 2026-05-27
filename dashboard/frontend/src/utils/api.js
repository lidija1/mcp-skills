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

export const api = {
  // ── Health ────────────────────────────────────────────────────────────
  health: () => get('/api/health'),

  // ── Jobs ──────────────────────────────────────────────────────────────
  listJobs: () => get('/api/jobs'),
  getJob: id => get(`/api/jobs/${id}`),
  explorerPrompt: prompt => post('/api/explorer/prompt', { prompt }),
  explorerRun: prompt => post('/api/explorer/run', { prompt }),

  // ── Policy ────────────────────────────────────────────────────────────
  getArchetypes: (lob = '') => get(`/api/policy/archetypes?lob=${lob}`),
  createPersona: (lob, description) => post('/api/policy/create-persona', { lob, description }),
  runFlow: (lob, persona_json) => post('/api/policy/run-flow', { lob, persona_json }),
  quickRun: (lob, description) => post('/api/policy/quick-run', { lob, description }),
  batchRun: scenarios => post('/api/policy/batch-run', { scenarios }),

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
