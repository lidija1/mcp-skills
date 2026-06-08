import {useState, useEffect, useCallback, useRef} from 'react'
import Header from './components/Header'
import OverviewPanel from './components/OverviewPanel'
import PolicyPanel from './components/PolicyPanel'
import ApiAssertionsPanel from './components/ApiAssertionsPanel'
import SettingsPanel from './components/SettingsPanel'
import JobsPanel from './components/JobsPanel'
import ChatPanel from './components/ChatPanel'
import ReportModal from './components/ReportModal'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import {
    Routes,
    Route,
    Navigate,
    useNavigate,
    useLocation,
} from 'react-router-dom'


import {api} from './utils/api'
import {
    AlertTriangle,
    CircleHelp,
    CalendarDays,
    CheckCircle2,
    ClipboardCheck,
    Home,
    Maximize2,
    Menu,
    MessageCircle,
    PanelRight,
    Settings,
    Trash2,
    UserCircle,
    Workflow,
    X,
} from 'lucide-react'
import {cleanDisplayText} from './utils/text'

function normalizeJobUpdate(job, update) {
    if (!update) return job

    if (update.error === 'not found') {
        return {
            ...job,
            status: 'error',
            error: 'This running job was not found in the backend. Start it again to rerun the test.',
            finished: job.finished ?? Date.now() / 1000,
        }
    }

    return {...job, ...update}
}

export default function App() {
    // const [tab, setTab] = useState('overview')
    const navigate = useNavigate()
    const location = useLocation()
    const [jobs, setJobs] = useState([])
    const [jobPopups, setJobPopups] = useState([])
    const [backendOk, setBackendOk] = useState(null)
    const [dashboardUser, setDashboardUser] = useState(null)
    const [authChecked, setAuthChecked] = useState(false)
    const [showRegister, setShowRegister] = useState(false)
    const [selectedJob, setSelectedJob] = useState(null)
    const [showHelp, setShowHelp] = useState(false)
    const [navCollapsed, setNavCollapsed] = useState(false)
    const [navMobileOpen, setNavMobileOpen] = useState(false)
    const [isNarrowNav, setIsNarrowNav] = useState(false)
    const [validationTab, setValidationTab] = useState('sweep')
    const [validationHistoryFilter, setValidationHistoryFilter] = useState('all')
    const [validationExpandedReportId, setValidationExpandedReportId] = useState(null)
    const [chatView, setChatView] = useState(() => localStorage.getItem('chatView') || 'sidebar')
    const [chatSidebarWidth, setChatSidebarWidth] = useState(() => {
        const saved = Number(localStorage.getItem('chatSidebarWidth'))
        return Number.isFinite(saved) && saved > 0 ? saved : null
    })
    const [toast, setToast] = useState(null)
    const toastTimerRef = useRef(null)

    const setChatViewPersist = v => { setChatView(v); localStorage.setItem('chatView', v) }

    const clampChatSidebarWidth = useCallback(width => {
        const navWidth = isNarrowNav ? 0 : navCollapsed ? 80 : 260
        const maxAvailable = Math.max(380, window.innerWidth - navWidth - 520)
        const maxWidth = Math.min(760, maxAvailable)

        return Math.round(Math.min(Math.max(width, 320), maxWidth))
    }, [isNarrowNav, navCollapsed])

    const persistChatSidebarWidth = useCallback(width => {
        const next = clampChatSidebarWidth(width)
        setChatSidebarWidth(next)
        localStorage.setItem('chatSidebarWidth', String(next))
    }, [clampChatSidebarWidth])

    const adjustChatSidebarWidth = useCallback(delta => {
        const measuredWidth = document.querySelector('.chat-sidebar')?.getBoundingClientRect().width
        const currentWidth = chatSidebarWidth || measuredWidth || 420
        persistChatSidebarWidth(currentWidth + delta)
    }, [chatSidebarWidth, persistChatSidebarWidth])

    const startChatResize = useCallback(e => {
        if (chatView !== 'sidebar' || isNarrowNav) return

        e.preventDefault()
        document.body.classList.add('is-resizing-chat')
        persistChatSidebarWidth(window.innerWidth - e.clientX)

        const handlePointerMove = event => {
            persistChatSidebarWidth(window.innerWidth - event.clientX)
        }
        const stopResize = () => {
            document.body.classList.remove('is-resizing-chat')
            window.removeEventListener('pointermove', handlePointerMove)
            window.removeEventListener('pointerup', stopResize)
            window.removeEventListener('pointercancel', stopResize)
        }

        window.addEventListener('pointermove', handlePointerMove)
        window.addEventListener('pointerup', stopResize)
        window.addEventListener('pointercancel', stopResize)
    }, [chatView, isNarrowNav, persistChatSidebarWidth])

    const handleChatResizeKeyDown = useCallback(e => {
        if (chatView !== 'sidebar' || isNarrowNav) return
        if (e.key === 'ArrowLeft') {
            e.preventDefault()
            adjustChatSidebarWidth(24)
        }
        if (e.key === 'ArrowRight') {
            e.preventDefault()
            adjustChatSidebarWidth(-24)
        }
    }, [adjustChatSidebarWidth, chatView, isNarrowNav])

    useEffect(() => {
        if (!chatSidebarWidth || chatView !== 'sidebar') return
        const next = clampChatSidebarWidth(chatSidebarWidth)
        if (next !== chatSidebarWidth) {
            setChatSidebarWidth(next)
            localStorage.setItem('chatSidebarWidth', String(next))
        }
    }, [chatSidebarWidth, chatView, clampChatSidebarWidth])

    const showToast = useCallback((message, options = {}) => {
        window.clearTimeout(toastTimerRef.current)
        setToast({
            id: Date.now(),
            message,
            tone: options.tone || 'success',
            icon: options.icon || 'check',
        })
        toastTimerRef.current = window.setTimeout(() => setToast(null), options.duration || 2200)
    }, [])

    useEffect(() => () => window.clearTimeout(toastTimerRef.current), [])

    useEffect(() => {
        const media = window.matchMedia('(max-width: 1040px)')
        const update = () => {
            setIsNarrowNav(media.matches)
            if (!media.matches) setNavMobileOpen(false)
        }

        update()
        if (media.addEventListener) {
            media.addEventListener('change', update)
            return () => media.removeEventListener('change', update)
        }

        media.addListener(update)
        return () => media.removeListener(update)
    }, [])

    useEffect(() => {
        if (chatView !== 'full') return
        const handler = e => { if (e.key === 'Escape') setChatViewPersist('sidebar') }
        document.addEventListener('keydown', handler)
        return () => document.removeEventListener('keydown', handler)
    }, [chatView])
    const [theme, setTheme] = useState(() => localStorage.getItem('dashboardTheme') || 'light')
    const previousJobStatusRef = useRef(null)

    useEffect(() => {
        document.documentElement.dataset.theme = theme
        localStorage.setItem('dashboardTheme', theme)
    }, [theme])

    useEffect(() => {
        api.health()
            .then(() => setBackendOk(true))
            .catch(() => setBackendOk(false))
    }, [])

    const loadJobs = useCallback(async () => {
    try {
        const persistedJobs = await api.listJobs()

        if (Array.isArray(persistedJobs)) {
            setJobs(persistedJobs)
        }
    } catch (err) {
        console.error(err)
    }
}, [])

    const updateJob = useCallback((jobId, patch) => {
        setJobs(prev => prev.map(job => (job.id === jobId ? {...job, ...patch} : job)))
    }, [])

    const cancelJob = useCallback(async job => {
        try {
            const data = await api.cancelJob(job.id)
            updateJob(job.id, data?.job || {
                status: 'canceled',
                error: 'Canceled by user',
                finished: Date.now() / 1000,
                current_status: null,
            })
            await loadJobs()
        } catch (err) {
            console.error(err)
        }
    }, [loadJobs, updateJob])

    const deleteJob = useCallback(async job => {
        await api.deleteJob(job.id)
        setJobs(prev => prev.filter(item => item.id !== job.id))
        setJobPopups(prev => prev.filter(item => item.job?.id !== job.id))
        setSelectedJob(current => (current?.id === job.id ? null : current))
        showToast('Deleted', {tone: 'danger', icon: 'trash'})
        await loadJobs()
    }, [loadJobs, showToast])

    useEffect(() => {
        let cancelled = false

        async function restoreSession() {
            try {
                const data = await api.me()
                if (cancelled) return
                setDashboardUser(data.user)
                const persistedJobs = await api.listJobs()
                if (!cancelled && Array.isArray(persistedJobs)) {
                    setJobs(persistedJobs)
                }
            } catch {
                if (!cancelled) {
                    setDashboardUser(null)
                    setJobs([])
                }
            } finally {
                if (!cancelled) setAuthChecked(true)
            }
        }

        restoreSession()

        return () => {
            cancelled = true
        }
    }, [])

    useEffect(() => {
        const running = jobs.filter(j => j.status === 'running')
        if (running.length === 0) return

        const timer = setInterval(async () => {
            const updates = await Promise.all(
                running.map(j => api.getJob(j.id).catch(() => ({id: j.id, status: 'running'})))
            )
            setJobs(prev =>
                prev.map(j => {
                    const upd = updates.find(u => u.id === j.id)
                    return normalizeJobUpdate(j, upd)
                })
            )
        }, 2500)

        return () => clearInterval(timer)
    }, [jobs])

    useEffect(() => {
        if (previousJobStatusRef.current === null) {
            previousJobStatusRef.current = new Map(jobs.map(job => [job.id, job.status]))
            return
        }

        const previousStatuses = previousJobStatusRef.current
        const completedJobs = jobs.filter(job => previousStatuses.get(job.id) === 'running' && job.status === 'done')
        if (completedJobs.length > 0) {
            setJobPopups(prev => {
                const existingIds = new Set(prev.map(item => item.id))
                const next = completedJobs
                    .filter(job => !existingIds.has(job.id))
                    .map(job => ({id: job.id, job}))
                return [...next, ...prev].slice(0, 3)
            })
        }

        previousJobStatusRef.current = new Map(jobs.map(job => [job.id, job.status]))
    }, [jobs])

    useEffect(() => {
        if (jobPopups.length === 0) return
        const timers = jobPopups.map(popup =>
            setTimeout(() => {
                setJobPopups(prev => prev.filter(item => item.id !== popup.id))
            }, 15000)
        )
        return () => timers.forEach(clearTimeout)
    }, [jobPopups])

    useEffect(() => {
        if (!selectedJob) return
        const latestJob = jobs.find(job => job.id === selectedJob.id)
        if (latestJob && latestJob !== selectedJob) {
            setSelectedJob(latestJob)
        }
    }, [jobs, selectedJob])

    const submitJob = useCallback(async (apiFn, label, options = {}) => {
        const data = await apiFn()
        if (!data.job_id) return
        const placeholder = {
            id: data.job_id,
            label,
            execution_type: options.executionType || options.execution_type || null,
            status: 'running',
            started: Date.now() / 1000,
            result: null,
            error: null,
            finished: null,
            metadata: options.metadata || {},
        }
        setJobs(prev => [placeholder, ...prev])
        return data.job_id
    }, [])

    const trackJob = useCallback((jobId, label, options = {}) => {
        const placeholder = {
            id: jobId,
            label,
            execution_type: options.executionType || options.execution_type || null,
            status: 'running',
            started: Date.now() / 1000,
            result: null,
            error: null,
            finished: null,
            metadata: options.metadata || {},
        }
        setJobs(prev => {
            if (prev.some(j => j.id === jobId)) return prev
            return [placeholder, ...prev]
        })
    }, [])

    const rerunJobFromReport = useCallback(async job => {
        const data = await api.rerunJob(job.id)
        if (data?.job_id) {
            trackJob(data.job_id, job.label, {metadata: job.metadata || {}})
        }
        await loadJobs()
        setSelectedJob(null)
    }, [loadJobs, trackJob])

    const rerunCanceledJob = useCallback(async job => {
        try {
            const data = await api.rerunJob(job.id)
            if (data?.job_id) {
                trackJob(data.job_id, job.label, {metadata: job.metadata || {}})
            }
            await loadJobs()
        } catch (err) {
            console.error(err)
        }
    }, [loadJobs, trackJob])

    const dismissJobPopup = useCallback(jobId => {
        setJobPopups(prev => prev.filter(item => item.id !== jobId))
    }, [])

    const openJobReportFromPopup = useCallback(job => {
        const latest = jobs.find(item => item.id === job.id) || job
        setSelectedJob(latest)
        dismissJobPopup(job.id)
    }, [dismissJobPopup, jobs])

    const login = useCallback(async user => {
        localStorage.removeItem('dashboardUser')
        localStorage.removeItem('access_token')
        setDashboardUser(user)
        setShowRegister(false)
        try {
            const persistedJobs = await api.listJobs()
            setJobs(Array.isArray(persistedJobs) ? persistedJobs : [])
        } catch {
            setJobs([])
        }
        navigate('/dashboard')
    }, [])

    const logout = useCallback(async () => {
        try {
            await api.logout()
        } catch {
            // Logout should still clear the local view if the backend is temporarily unavailable.
        }
        localStorage.removeItem('selectedLob')
        localStorage.removeItem('dashboardUser')
        localStorage.removeItem('access_token')
        setDashboardUser(null)
        setJobs([])
        navigate('/login')
    }, [])

    if (!authChecked) {
        return (
            <main className="auth-page">
                <section className="auth-card">
                    <p className="auth-subtitle">Checking dashboard session...</p>
                </section>
            </main>
        )
    }

    if (!dashboardUser) {
        if (showRegister) {
            return (
                <RegisterPage
                    onBackToLogin={() => setShowRegister(false)}
                />
            )
        }

        return (
            <LoginPage
                onLogin={login}
                onCreateAccount={() => setShowRegister(true)}
            />
        )
    }

    const currentPath = location.pathname
    const pageKey = currentPath.startsWith('/uw-tests') || currentPath.startsWith('/api-tests')
        ? 'uw-tests'
        : currentPath === '/settings'
            ? 'settings'
            : currentPath === '/jobs'
                ? 'jobs'
                : currentPath === '/dashboard'
                    ? 'overview'
                    : 'default'

    const requireAuth = component => {
        if (!dashboardUser) {
            return <Navigate to="/login" replace/>
        }
        return component
    }

    const togglePrimaryNav = () => {
        if (isNarrowNav) {
            setNavMobileOpen(open => !open)
            return
        }

        setNavCollapsed(collapsed => !collapsed)
    }

    const closeMobileNav = () => {
        if (isNarrowNav) setNavMobileOpen(false)
    }

    const workspaceStyle = chatView === 'sidebar' && chatSidebarWidth
        ? {'--chat-sidebar-width': `${chatSidebarWidth}px`}
        : undefined

    return (
        <div className="app-shell">
            <Header backendOk={backendOk} user={dashboardUser} onLogout={logout}/>

            <div
                className={`workspace${chatView === 'hidden' ? ' workspace--chat-hidden' : ''}${navCollapsed ? ' workspace--nav-collapsed' : ''}${navMobileOpen ? ' workspace--nav-open' : ''}`}
                style={workspaceStyle}
            >
                <aside
                    className="side-nav"
                    aria-label="Primary navigation"
                    aria-hidden={isNarrowNav && !navMobileOpen}
                    inert={isNarrowNav && !navMobileOpen ? '' : undefined}
                >
                    <nav className="side-nav-main">
                        <IconButton
                            icon={Menu}
                            label={isNarrowNav && navMobileOpen ? 'Close menu' : 'Menu'}
                            onClick={togglePrimaryNav}
                            expanded={isNarrowNav ? navMobileOpen : !navCollapsed}
                        />
                        {/*<NavItem icon={Home} label="Overview" active={tab === 'overview'}*/}
                        {/*         onClick={() => setTab('overview')}/>*/}
                        {/*<NavItem icon={CalendarDays} label="Jobs" active={tab === 'jobs'}*/}
                        {/*         onClick={() => setTab('jobs')}/>*/}
                        {/*<NavItem icon={Workflow} label="Policy Flow" active={tab === 'policy'}*/}
                        {/*         onClick={() => setTab('policy')}/>*/}
                        <NavItem
                            icon={Home}
                            label="Overview"
                            active={currentPath === '/dashboard'}
                            onClick={() => {
                                navigate('/dashboard')
                                closeMobileNav()
                            }}
                        />

                        <NavItem
                            icon={CalendarDays}
                            label="Jobs"
                            active={currentPath === '/jobs'}
                            onClick={() => {
                                navigate('/jobs')
                                closeMobileNav()
                            }}
                        />

                        <NavItem
                            icon={Workflow}
                            label="Policy Flow"
                            active={currentPath.startsWith('/policy-flow')}
                            onClick={() => {
                                const savedLob = localStorage.getItem('selectedLob') || 'personal-auto'
                                navigate(`/policy-flow/${savedLob}`)
                                closeMobileNav()
                            }}
                        />
                        <NavItem
                            icon={ClipboardCheck}
                            label="Validation Tests"
                            active={currentPath.startsWith('/uw-tests') || currentPath.startsWith('/api-tests')}
                            onClick={() => {
                                navigate('/uw-tests')
                                closeMobileNav()
                            }}
                        />
                        <NavItem
                            icon={Settings}
                            label="Settings"
                            active={currentPath === '/settings'}
                            onClick={() => {
                                navigate('/settings')
                                closeMobileNav()
                            }}
                        />
                    </nav>
                    <nav className="side-nav-footer">
                        <NavItem
                            icon={CircleHelp}
                            label="Help"
                            onClick={() => {
                                setShowHelp(true)
                                closeMobileNav()
                            }}
                        />
                        <NavItem icon={UserCircle} label="Account"/>
                    </nav>
                </aside>

                {navMobileOpen && (
                    <button
                        className="side-nav-backdrop"
                        type="button"
                        aria-label="Close menu"
                        onClick={() => setNavMobileOpen(false)}
                    />
                )}

                <button
                    className="nav-mobile-toggle"
                    type="button"
                    title="Menu"
                    aria-label="Menu"
                    aria-expanded={navMobileOpen}
                    onClick={togglePrimaryNav}
                >
                    <Menu size={22} strokeWidth={2}/>
                </button>

                <main className={`content-pane content-pane--${pageKey}`}>
                    {backendOk === false && (
                        <div className="status-alert">
                            Backend not reachable. Start it with <code>python dashboard/backend/main.py</code>
                        </div>
                    )}
                    <Routes>
                        <Route
                            path="/dashboard"
                            element={requireAuth(
                                <OverviewPanel
                                    backendOk={backendOk}
                                    jobs={jobs}
                                    onOpenReport={setSelectedJob}
                                    onCancelJob={cancelJob}
                                    onRerunJob={rerunCanceledJob}
                                />
                            )}
                        />

                        <Route
                            path="/jobs"
                            element={requireAuth(
                                <JobsPanel
                                    jobs={jobs}
                                    currentUser={dashboardUser}
                                    onSelect={setSelectedJob}
                                    onClearHistory={() => setJobs([])}
                                    onRefreshJobs={loadJobs}
                                    onUpdateJob={updateJob}
                                    onDeleteJob={deleteJob}
                                />
                            )}
                        />

                        <Route
                            path="/policy-flow/:lob"
                            element={requireAuth(
                                <PolicyPanel submitJob={submitJob}/>
                            )}
                        />

                        <Route
                            path="/policy-flow"
                            element={
                                <Navigate
                                    to={`/policy-flow/${localStorage.getItem('selectedLob') || 'personal-auto'}`}
                                    replace
                                />
                            }
                        />
                        <Route
                            path="/uw-tests"
                            element={requireAuth(
                                <ApiAssertionsPanel
                                    submitJob={submitJob}
                                    activeTab={validationTab}
                                    onActiveTabChange={setValidationTab}
                                    historyFilter={validationHistoryFilter}
                                    onHistoryFilterChange={setValidationHistoryFilter}
                                    expandedId={validationExpandedReportId}
                                    onExpandedIdChange={setValidationExpandedReportId}
                                />
                            )}
                        />
                        <Route path="/api-tests" element={<Navigate to="/uw-tests" replace/>}/>
                        <Route
                            path="/settings"
                            element={requireAuth(
                                <SettingsPanel theme={theme} onThemeChange={setTheme}/>
                            )}
                        />
                        <Route path="/" element={<Navigate to="/dashboard" replace/>}/>
                    </Routes>
                </main>

                <aside
                    className={`chat-sidebar${chatView === 'full' ? ' chat-sidebar--expanded' : ''}${chatView === 'hidden' ? ' chat-sidebar--hidden' : ''}`}
                    aria-label="Chat assistant"
                >
                    {chatView === 'full' && (
                        <div className="chat-sidebar-backdrop" onClick={() => setChatViewPersist('sidebar')} />
                    )}
                    {chatView === 'sidebar' && (
                        <div
                            className="chat-resize-handle"
                            role="separator"
                            aria-label="Resize chat"
                            aria-orientation="vertical"
                            tabIndex={0}
                            onPointerDown={startChatResize}
                            onKeyDown={handleChatResizeKeyDown}
                        />
                    )}
                    <div className="chat-sidebar-inner">
                        <div className="chat-sidebar-header">
                            <MessageCircle size={17}/>
                            <span className="chat-sidebar-title">Chat Assistant</span>
                            <div className="chat-header-btns">
                                <button
                                    className={`chat-expand-btn${chatView === 'sidebar' ? ' chat-expand-btn--active' : ''}`}
                                    type="button"
                                    aria-label="Sidebar view"
                                    onClick={() => setChatViewPersist('sidebar')}
                                    title="Sidebar"
                                >
                                    <PanelRight size={15}/>
                                </button>
                                <button
                                    className={`chat-expand-btn${chatView === 'full' ? ' chat-expand-btn--active' : ''}`}
                                    type="button"
                                    aria-label="Full view"
                                    onClick={() => setChatViewPersist('full')}
                                    title="Expand"
                                >
                                    <Maximize2 size={15}/>
                                </button>
                                <button
                                    className="chat-expand-btn"
                                    type="button"
                                    aria-label="Hide chat"
                                    onClick={() => setChatViewPersist('hidden')}
                                    title="Hide"
                                >
                                    <X size={15}/>
                                </button>
                            </div>
                        </div>
                        <ChatPanel
                            onJobDispatched={trackJob}
                            jobs={jobs}
                            onOpenReport={setSelectedJob}
                            expanded={chatView === 'full'}
                        />
                    </div>
                </aside>

                {chatView === 'hidden' && (
                    <div className="chat-fab" aria-label="Open chat">
                        <span className="chat-fab-label"><MessageCircle size={14}/> Chat</span>
                        <button
                            className="chat-fab-btn"
                            type="button"
                            title="Open as sidebar"
                            onClick={() => setChatViewPersist('sidebar')}
                        >
                            <PanelRight size={16}/>
                        </button>
                        <button
                            className="chat-fab-btn"
                            type="button"
                            title="Open full"
                            onClick={() => setChatViewPersist('full')}
                        >
                            <Maximize2 size={16}/>
                        </button>
                    </div>
                )}

                <JobDonePopups
                    popups={jobPopups}
                    onOpenReport={openJobReportFromPopup}
                    onDismiss={dismissJobPopup}
                />

                {selectedJob && (
                    <ReportModal
                        job={selectedJob}
                        onClose={() => setSelectedJob(null)}
                        onRerun={rerunJobFromReport}
                        currentUser={dashboardUser}
                        onDelete={deleteJob}
                        onNotify={showToast}
                    />
                )}
                {showHelp && <HelpModal onClose={() => setShowHelp(false)}/>}
                <AppToast toast={toast} onDismiss={() => setToast(null)}/>
            </div>
        </div>
    )
}

function AppToast({toast, onDismiss}) {
    if (!toast) return null
    const Icon = toast.icon === 'trash' ? Trash2 : CheckCircle2

    return (
        <div className="app-toast-wrap" aria-live="polite" aria-atomic="true">
            <section className={`app-toast ${toast.tone || 'success'}`}>
                <Icon size={17}/>
                <span>{toast.message}</span>
                <button className="app-toast-close" type="button" aria-label="Dismiss notification" onClick={onDismiss}>
                    <X size={14}/>
                </button>
            </section>
        </div>
    )
}

function isUwReferralJob(job) {
    const text = `${job?.result || ''} ${job?.error || ''}`.toLowerCase()
    return text.includes('uw referral') || text.includes('uw conditions triggered')
}

function JobDonePopups({popups, onOpenReport, onDismiss}) {
    if (popups.length === 0) return null

    return (
        <div className="job-popup-stack" aria-live="polite" aria-label="Job notifications">
            {popups.map(({id, job}) => (
                <section className={`job-done-popup ${isUwReferralJob(job) ? 'warning' : ''}`} key={id}>
                    <div className="job-done-icon">
                        {isUwReferralJob(job) ? <AlertTriangle size={20}/> : <CheckCircle2 size={20}/>}
                    </div>
                    <div className="job-done-copy">
                        <strong>{isUwReferralJob(job) ? 'UW referral triggered' : 'Job completed'}</strong>
                        <span>{cleanDisplayText(job.label)}</span>
                    </div>
                    <button className="job-done-link" type="button" onClick={() => onOpenReport(job)}>
                        Open report
                    </button>
                    <button
                        className="job-done-dismiss"
                        type="button"
                        aria-label="Dismiss notification"
                        onClick={() => onDismiss(id)}
                    >
                        <X size={16}/>
                    </button>
                </section>
            ))}
        </div>
    )
}

function IconButton({icon: Icon, label, onClick, expanded}) {
    return (
        <button
            className="nav-icon-button"
            type="button"
            title={label}
            aria-label={label}
            aria-expanded={expanded}
            onClick={onClick}
        >
            <Icon size={22} strokeWidth={2}/>
        </button>
    )
}

function NavItem({icon: Icon, label, active, onClick}) {
    return (
        <button
            className={`nav-item ${active ? 'active' : ''}`}
            onClick={onClick}
            type="button"
            title={label}
            aria-label={label}
        >
            <Icon size={22} strokeWidth={2}/>
            <span>{label}</span>
        </button>
    )
}

function HelpModal({onClose}) {
    const sections = [
        {
            title: 'Overview',
            summary: 'Start here when you want a quick operational view of the dashboard.',
            items: [
                'Backend shows whether FastAPI is reachable.',
                'Saved jobs and running jobs show current automation volume.',
                'Results separates completed, failed, and canceled runs.',
                'Live Automation Activity Feed lets you open reports, cancel active runs, or rerun eligible flows.',
            ],
        },
        {
            title: 'Policy Flow',
            summary: 'Use this page to generate customer data and run end-to-end policy workflows.',
            items: [
                'Line of Business selects the workflow. Current options are Personal Auto and Homeowner.',
                'Quick Policy Test accepts a plain-English customer or risk description and runs the full journey automatically.',
                'Build Customer Profile turns a natural-language description into structured test data JSON.',
                'Run Policy Journey accepts profile JSON from Build Customer Profile, or a saved test case id such as TC_ID_0001.',
            ],
            fieldTips: [
                'For plain-English fields, include the risk details that matter: age, coverage, vehicle use, license status, SR-22, prior losses, roof age, zone, or claims history.',
                'For JSON fields, paste the generated profile exactly as returned, or enter one TC_ID when you want to replay existing static test data.',
            ],
        },
        {
            title: 'Validation Tests',
            summary: 'Use this page when you want evidence checks without binding a policy.',
            items: [
                'Regression Sweep starts from a clean baseline and generates rating variants automatically.',
                'Focus category narrows the sweep to All categories, Risk adding only, Discounts only, Hard stops only, or Ladder only.',
                'Direct Assert validates a specific premium or total cost against the actual OneShield result.',
                'History stores prior assertion results and lets you review pass/fail detail, coverage premiums, UW conditions, and persona JSON.',
            ],
            fieldTips: [
                'Driver profile can be preset or Custom age. Exact age is only used when Custom age is selected.',
                'Coverage, Vehicle use, Gender, Marital status, License, SR-22, and Ownership shape the generated persona.',
                'Assertion type can check Total premium from Rating Detail or Total cost from Verify Billing.',
                'Operator controls the comparison: approximate with tolerance, exact match, greater than, or less than.',
            ],
        },
        {
            title: 'Chat Assistant',
            summary: 'Use chat when you want to ask questions, learn details, or dispatch supported automation from natural language.',
            items: [
                'Ask mode is read-only guidance. Use it for explanations, project structure, field meaning, examples, and how-to questions.',
                'Tools mode can start approved actions such as quick policy runs, persona generation, persona variations, batch tests, UW audits, rule tests, full audits, and premium or total-cost assertions.',
                'Use /help for a structured dashboard overview, or /help chat, /help tools, /help api, /help uw, /help persona, /help lob, and related topics for deeper guidance.',
                'When Tools mode needs confirmation, review the generated parameters and click Confirm before the run starts.',
            ],
            fieldTips: [
                'Good chat prompts include the LOB, the action you want, and the important facts: for example, "run an auto policy flow for a 23-year-old driver with SR-22 and Gold coverage."',
                'Ask can explain how to fill fields; Tools can execute only the whitelisted automation actions.',
            ],
        },
        {
            title: 'Account',
            summary: 'Use the account area for the current signed-in dashboard session.',
            items: [
                'Your profile is shown in the top bar.',
                'Use Logout when you want to end the current browser session.',
            ],
        },
    ]

    useEffect(() => {
        const handler = e => {
            if (e.key === 'Escape') onClose()
        }
        document.addEventListener('keydown', handler)
        return () => document.removeEventListener('keydown', handler)
    }, [onClose])

    return (
        <div className="help-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Help">
            <div className="help-modal" onClick={e => e.stopPropagation()}>
                <div className="help-modal-header">
                    <h2>How to use INFORCE</h2>
                    <button className="help-modal-close" onClick={onClose} aria-label="Close help" type="button">
                        <X size={18}/>
                    </button>
                </div>
                <div className="help-modal-body">
                    <p className="help-intro">
                        This guide follows the main menu order and highlights what each area is for, which options are
                        available, and how to use the important fields.
                    </p>
                    <div className="help-section-grid">
                        {sections.map(section => (
                            <section className="help-section" key={section.title}>
                                <h3>{section.title}</h3>
                                <p>{section.summary}</p>
                                <ul>
                                    {section.items.map(item => <li key={item}>{item}</li>)}
                                </ul>
                                {section.fieldTips && (
                                    <div className="help-field-tips">
                                        <strong>Field tips</strong>
                                        <ul>
                                            {section.fieldTips.map(item => <li key={item}>{item}</li>)}
                                        </ul>
                                    </div>
                                )}
                            </section>
                        ))}
                    </div>
                    <div className="help-note">
                        To learn more details, use the chat options. Ask mode is best for explanations and field
                        guidance; Tools mode is best when you want the assistant to run an approved automation.
                    </div>
                </div>
            </div>
        </div>
    )
}
