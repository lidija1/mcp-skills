import {cleanDisplayText} from '../utils/text'
import {canRerunJob, inferExecutionType, shouldShowRerunAction} from '../utils/jobRerun'
import {resolveJobLobDisplay, sortLobGroupKeys} from '../utils/jobLob'
import {useEffect, useState} from 'react'
import { getDisplayStatus } from '../utils/jobStatus.js'
import {api} from '../utils/api'
import ConfirmDeleteModal from './ConfirmDeleteModal'
import {BriefcaseBusiness, CalendarDays, ChevronRight, FileText, RotateCw, Trash2, X} from 'lucide-react'

function elapsed(job) {
    const end = job.finished ?? Date.now() / 1000
    const secs = Math.max(0, Math.round(end - job.started))
    if (secs < 60) return `${secs}s`
    return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

function startedTime(job) {
    return new Date(job.started * 1000).toLocaleTimeString(undefined, {
        hour: 'numeric', minute: '2-digit',
    })
}

function dayLabel(job) {
    const date = new Date(job.started * 1000)
    const today = new Date()
    const yesterday = new Date()
    yesterday.setDate(today.getDate() - 1)
    const dateText = date.toLocaleDateString(undefined, {
        month: 'short', day: 'numeric', year: 'numeric',
    })

    if (date.toDateString() === today.toDateString()) return `Today - ${dateText}`
    if (date.toDateString() === yesterday.toDateString()) return `Yesterday - ${dateText}`

    return date.toLocaleDateString(undefined, {
        weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
    })
}

function groupJobs(jobs) {
    return jobs.reduce((days, job) => {
        const day = dayLabel(job)
        const lob = resolveJobLobDisplay(job)

        if (!days[day]) days[day] = {}
        if (!days[day][lob]) days[day][lob] = []
        days[day][lob].push(job)

        return days
    }, {})
}

export async function rerunJob(jobId) {
    return api.rerunJob(jobId)
}

const DELETABLE_STATUSES = new Set(['done', 'error', 'failed', 'canceled', 'cancelled'])

function canDeleteJob(job, currentUser) {
    if (!job || !currentUser) return false
    return DELETABLE_STATUSES.has(getDisplayStatus(job)) && (job.created_by === currentUser.id || job.created_by == null)
}

export default function JobsPanel({jobs, currentUser, onSelect, onClearHistory, onRefreshJobs, onUpdateJob, onDeleteJob}) {
    const grouped = groupJobs(jobs)
    const total = jobs.length
    // const running = jobs.filter(job => job.status === 'running').length
    // const completed = jobs.filter(job => job.status === 'done').length
    // const failed = jobs.filter(job => job.status === 'error').length
    // const canceled = jobs.filter(job => job.status === 'canceled').length


    const completed = jobs.filter(j => getDisplayStatus(j) === 'done').length
    const failed = jobs.filter(j => getDisplayStatus(j) === 'failed' || getDisplayStatus(j) === 'error').length
    const canceled = jobs.filter(j => getDisplayStatus(j) === 'canceled').length
    const running = jobs.filter(j => getDisplayStatus(j) === 'running').length


    async function handleRerun(job) {
        try {
            await rerunJob(job.id)

            if (onRefreshJobs) {
                await onRefreshJobs()
            }
        } catch (err) {
            console.error(err)
        }
    }

    function toggleDay(day) {
        setCollapsedDays(prev => ({
            ...prev, [day]: !prev[day],
        }))
    }

    function isTodayLabel(day) {
        return day.startsWith('Today')
    }

    const [collapsedDays, setCollapsedDays] = useState(() => {
        const saved = localStorage.getItem('jobs-collapsed-days')

        if (saved) {
            return JSON.parse(saved)
        }

        const initial = {}

        Object.keys(grouped).forEach(day => {
            initial[day] = !isTodayLabel(day)
        })

        return initial
    })
    useEffect(() => {
        localStorage.setItem(
            'jobs-collapsed-days',
            JSON.stringify(collapsedDays)
        )
    }, [collapsedDays])

    const [deleteTarget, setDeleteTarget] = useState(null)
    const [deleteError, setDeleteError] = useState('')
    const [deleting, setDeleting] = useState(false)


    async function handleCancel(job) {
        try {
            const data = await api.cancelJob(job.id)

            if (onUpdateJob) {
                onUpdateJob(job.id, data?.job || {
                    status: 'canceled',
                    error: 'Canceled by user',
                    finished: Date.now() / 1000,
                    current_status: null,
                })
            }

            if (onRefreshJobs) {
                await onRefreshJobs()
            }
        } catch (err) {
            console.error(err)
        }
    }

    async function handleConfirmDelete() {
        if (!deleteTarget || !onDeleteJob || deleting) return
        setDeleting(true)
        setDeleteError('')
        try {
            await onDeleteJob(deleteTarget)
            setDeleteTarget(null)
        } catch (err) {
            setDeleteError(err.message || 'Could not delete this job.')
        } finally {
            setDeleting(false)
        }
    }

    return (<div className="panel-stack jobs-panel-page">
        <div className="jobs-toolbar">
            <div className="page-heading">
                <h1>Jobs</h1>
                <p>Local dashboard history grouped by day and line of business.</p>
            </div>
            {total > 0 && (<button className="text-button danger" type="button" onClick={onClearHistory}>
                Clear History
            </button>)}
        </div>

        <div className="jobs-summary-grid">
            <SummaryMetric label="Total jobs" value={total}/>
            <SummaryMetric label="Running" value={running}/>
            <SummaryMetric label="Completed" value={completed}/>
            <SummaryMetric label="Failed" value={failed}/>
            <SummaryMetric label="Canceled" value={canceled}/>
        </div>

        {total === 0 ? (<div className="empty-history">
            <h2>No saved jobs yet</h2>
            <p>Run a policy flow and it will be saved here in this browser.</p>
        </div>) : (<div className="jobs-table-card">
            <div className="jobs-table-header" role="row">
                <span>Job</span>
                <span>Status</span>
                <span>Started</span>
                <span>Duration</span>
                <span>Job ID</span>
                <span>Actions</span>
            </div>

            <div className="jobs-table-body">
                {Object.entries(grouped).map(([day, lobs]) => {
                    const dayCount = Object.values(lobs).reduce((sum, lobJobs) => sum + lobJobs.length, 0)

                    return (<section className="jobs-day-group" key={day}>
                        <button
                            className="jobs-group-row jobs-day-row"
                            onClick={() => toggleDay(day)}
                            type="button"
                            aria-expanded={!collapsedDays[day]}
                        >
                            <div className="jobs-group-title">
                                <span className="jobs-group-icon">
                                    <CalendarDays size={16}/>
                                </span>
                                <strong>{day}</strong>
                                <em>{dayCount} {dayCount === 1 ? 'job' : 'jobs'}</em>
                            </div>
                            <span className={`jobs-collapse-marker ${collapsedDays[day] ? 'collapsed' : ''}`}>
                                <ChevronRight size={18}/>
                            </span>
                        </button>

                        {!collapsedDays[day] &&
                            sortLobGroupKeys(Object.keys(lobs)).map(lob => {
                                const lobJobs = lobs[lob]
                                return (<div className="jobs-lob-group" key={`${day}-${lob}`}>
                                    <div className="jobs-group-row jobs-lob-row">
                                        <div className="jobs-group-title">
                                            <span className="jobs-group-icon">
                                                <BriefcaseBusiness size={15}/>
                                            </span>
                                            <strong>{lob}</strong>
                                            <em>{lobJobs.length} {lobJobs.length === 1 ? 'job' : 'jobs'}</em>
                                        </div>
                                    </div>

                                    {lobJobs.map(job => (
                                        <HistoryRow
                                            key={job.id}
                                            job={job}
                                            onSelect={onSelect}
                                            onRerun={handleRerun}
                                            onCancel={handleCancel}
                                            canDelete={canDeleteJob(job, currentUser)}
                                            onRequestDelete={target => {
                                                setDeleteError('')
                                                setDeleteTarget(target)
                                            }}
                                        />
                                    ))}
                                </div>)
                            })}
                    </section>)
                })}
            </div>
        </div>)}
        <ConfirmDeleteModal
            job={deleteTarget}
            deleting={deleting}
            error={deleteError}
            onCancel={() => {
                if (!deleting) setDeleteTarget(null)
            }}
            onConfirm={handleConfirmDelete}
        />
    </div>)
}

function SummaryMetric({label, value}) {
    return (<div className="summary-metric">
        <span>{label}</span>
        <strong>{value}</strong>
    </div>)
}


function HistoryRow({job, onSelect, onRerun, onCancel, canDelete, onRequestDelete}) {
    const displayStatus = getDisplayStatus(job)
    const outcomeBadge = getOutcomeBadge(job, displayStatus)
    const jobLabel = cleanDisplayText(job.label)
    const canOpen =
    displayStatus === 'done' ||
    displayStatus === 'error' ||
    displayStatus === 'failed'
    const isRunning = displayStatus === 'running' || job.status === 'running'
    const canRerun = !isRunning && (canRerunJob(job) || shouldShowRerunAction(job))
    const owner = job.created_by_user
    const ownerName = owner?.display_name || owner?.username

    return (<article
        className={`jobs-table-row ${displayStatus === 'error' ? 'has-error' : ''} ${displayStatus === 'canceled' ? 'is-canceled' : ''}`}>
        <div className="jobs-job-title">
            <strong title={jobLabel}>{jobLabel}</strong>
            {ownerName && <small className="jobs-owner">Created by {ownerName}</small>}
        </div>
        <div className="jobs-status-cell">
            <span className={`job-status ${displayStatus}`}>
              <i/>
                {statusLabel(displayStatus)}
            </span>
            {outcomeBadge && (
                <span className={`job-outcome-badge ${outcomeBadge.tone}`}>
                    {outcomeBadge.label}
                </span>
            )}
        </div>
        <div className="jobs-cell-muted">{startedTime(job)}</div>
        <div className="jobs-cell-muted">{elapsed(job)}</div>
        <div className="jobs-cell-id" title={job.id}>{job.id}</div>
        <div className="jobs-actions">
            {canOpen && (
                <div className="jobs-action-slot jobs-action-slot-secondary">
                    <button
                        className="jobs-icon-btn expand-on-hover"
                        data-label="view-report"
                        type="button"
                        title="View report"
                        aria-label="View report"
                        onClick={() => onSelect(job)}
                    >
                        <FileText size={16}/>
                        <span className="label">View report</span>
                    </button>
                </div>
            )}
            {canRerun && (
                <div className="jobs-action-slot jobs-action-slot-primary">
                    <button
                        className="jobs-icon-btn expand-on-hover"
                        data-label="run-again"
                        type="button"
                        title="Run again"
                        aria-label="Run again"
                        onClick={() => onRerun(job)}
                    >
                        <RotateCw size={16}/>
                        <span className="label">Run again</span>
                    </button>
                </div>
            )}
            {isRunning && (
                <div className="jobs-action-slot jobs-action-slot-primary jobs-action-slot-wide">
                    <button
                        className="jobs-icon-btn danger always-labeled"
                        type="button"
                        onClick={() => onCancel(job)}
                    >
                        <X size={16}/>
                        <span className="label">Cancel</span>
                    </button>
                </div>
            )}
            {canDelete && (
                <div className="jobs-action-slot jobs-action-slot-danger">
                    <button
                        className="jobs-icon-btn danger icon-only"
                        type="button"
                        title="Delete"
                        aria-label="Delete"
                        onClick={() => onRequestDelete(job)}
                    >
                        <Trash2 size={16}/>
                    </button>
                </div>
            )}
        </div>
        {getDisplayStatus(job) === 'error' && job.error && (<div className="job-error">{job.error}</div>)}
    </article>)
}

function statusLabel(status) {
    if (status === 'done') return 'Done'
    if (status === 'error') return 'Error'
    if (status === 'failed') return 'Failed'
    if (status === 'canceled' || status === 'cancelled') return 'Cancelled'
    return 'Running'
}

const ASSERTION_EXECUTION_TYPES = new Set([
    'api_assertion',
    'api_compare',
    'api_ladder',
    'api_ai_assert',
    'api_assert_flow',
    'regression_sweep',
])

function getOutcomeBadge(job, displayStatus) {
    if (displayStatus !== 'done') return null

    const assertionOutcome = getAssertionOutcome(job)
    if (assertionOutcome) {
        return {
            label: assertionOutcome === 'pass' ? 'Passed' : 'Failed',
            tone: assertionOutcome === 'pass' ? 'passed' : 'fail',
        }
    }

    if (hasUwReferralOutcome(job)) {
        return {label: 'UW Referral', tone: 'warning'}
    }

    return null
}

function getAssertionOutcome(job) {
    if (!isAssertionJob(job)) return null

    const rawResult = String(job?.result || '').trim()
    if (!rawResult) return null

    const jsonOutcome = getAssertionJsonOutcome(rawResult)
    if (jsonOutcome) return jsonOutcome

    if (hasAssertionFailed(rawResult)) return 'fail'
    if (hasAssertionPassed(rawResult)) return 'pass'

    return null
}

function isAssertionJob(job) {
    const type = inferExecutionType(job)
    if (ASSERTION_EXECUTION_TYPES.has(type)) return true

    const tool = job?.metadata?.tool
    if (tool === 'run_api_assertion') return true

    const label = String(job?.label || '').toLowerCase()
    return label.includes('assert') || label.includes('assertion')
}

function getAssertionJsonOutcome(rawResult) {
    if (!rawResult.startsWith('{')) return null

    try {
        const parsed = JSON.parse(rawResult)
        if (parsed?.passed === true) return 'pass'
        if (parsed?.passed === false) return 'fail'

        const status = String(parsed?.status || parsed?.result || '').toLowerCase()
        if (/\bfail(?:ed)?\b/.test(status)) return 'fail'
        if (/\bpass(?:ed)?\b/.test(status)) return 'pass'
    } catch {
        return null
    }

    return null
}

function hasAssertionFailed(rawResult) {
    return (
        /^#{1,6}\s+.*\b(?:FAIL|FAILED)\b/im.test(rawResult) ||
        /\*\*Status:\*\*\s*(?:[^A-Za-z\n]*\s*)?FAIL\b/i.test(rawResult)
    )
}

function hasAssertionPassed(rawResult) {
    return (
        /^#{1,6}\s+.*\b(?:PASS|ALL PASS)\b/im.test(rawResult) ||
        /\*\*Status:\*\*\s*(?:[^A-Za-z\n]*\s*)?PASS\b/i.test(rawResult)
    )
}

function hasUwReferralOutcome(job) {
    const type = inferExecutionType(job)
    const label = String(job?.label || '').toLowerCase()
    const isPolicyJob =
        type === 'quick_run' ||
        type === 'policy_flow' ||
        label.includes('quick policy') ||
        label.includes('policy journey')

    if (!isPolicyJob) return false

    const result = String(job?.result || '')
    return (
        /\|\s*\*\*Outcome\*\*\s*\|\s*[^|\n]*UW Referral/i.test(result) ||
        /\|\s*\*\*Status\*\*\s*\|\s*[^|\n]*UW REFERRAL/i.test(result) ||
        /^#{1,6}\s+UW Rules Triggered\b/im.test(result) ||
        /\bOutcome:\s*UW Referral\b/i.test(result)
    )
}
