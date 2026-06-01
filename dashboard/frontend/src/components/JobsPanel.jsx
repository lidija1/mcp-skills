import {cleanDisplayText} from '../utils/text'
import {resolveJobLobDisplay, sortLobGroupKeys} from '../utils/jobLob'
import {useEffect, useState} from 'react'
import {api} from '../utils/api'

const STATUS_CONFIG = {
    running: {color: '#2563eb', label: 'Running'},
    done: {color: '#16a34a', label: 'Done'},
    error: {color: '#dc2626', label: 'Error'},
    canceled: {color: '#d97706', label: 'Canceled'},
}

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

export default function JobsPanel({jobs, onSelect, onClearHistory, onRefreshJobs, onUpdateJob}) {
    const grouped = groupJobs(jobs)
    const total = jobs.length
    const running = jobs.filter(job => job.status === 'running').length
    const completed = jobs.filter(job => job.status === 'done').length
    const failed = jobs.filter(job => job.status === 'error').length
    const canceled = jobs.filter(job => job.status === 'canceled').length


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


    async function handleCancel(job) {
        try {
            await api.cancelJob(job.id)

            if (onUpdateJob) {
                onUpdateJob(job.id, {
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
                <span>Group / Job</span>
                <span>Status</span>
                <span>Started</span>
                <span>Duration</span>
                <span>ID</span>
                <span/>
            </div>

            <div className="jobs-table-body">
                {Object.entries(grouped).map(([day, lobs]) => {
                    const dayCount = Object.values(lobs).reduce((sum, lobJobs) => sum + lobJobs.length, 0)

                    return (<section className="jobs-day-group" key={day}>
                        <div
                            className="jobs-group-row jobs-day-row"
                            onClick={() => toggleDay(day)}
                            role="button"
                            tabIndex={0}
                        >
                            <div className="jobs-group-title">
                                <strong>{day}</strong>
                                <span>{dayCount} {dayCount === 1 ? 'job' : 'jobs'}</span>
                            </div>
                            <span
                                className={`jobs-collapse-marker ${collapsedDays[day] ? 'collapsed' : ''}`}>
                                                ›
                                        </span>
                        </div>

                        {!collapsedDays[day] &&
                            sortLobGroupKeys(Object.keys(lobs)).map(lob => {
                                const lobJobs = lobs[lob]
                                return (<div className="jobs-lob-group" key={`${day}-${lob}`}>
                                    <div className="jobs-group-row jobs-lob-row">
                                        <div className="jobs-group-title">
                                            <strong>{lob}</strong>
                                            <span>{lobJobs.length} {lobJobs.length === 1 ? 'job' : 'jobs'}</span>
                                        </div>
                                    </div>

                                    {lobJobs.map(job => (
                                        <HistoryRow
                                            key={job.id}
                                            job={job}
                                            onSelect={onSelect}
                                            onRerun={handleRerun}
                                            onCancel={handleCancel}
                                        />
                                    ))}
                                </div>)
                            })}
                    </section>)
                })}
            </div>
        </div>)}
    </div>)
}

function SummaryMetric({label, value}) {
    return (<div className="summary-metric">
        <span>{label}</span>
        <strong>{value}</strong>
    </div>)
}

function HistoryRow({job, onSelect, onRerun, onCancel}) {
    const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.running
    const canOpen = job.status === 'done' || job.status === 'error'
    const owner = job.created_by_user
    const ownerName = owner?.display_name || owner?.username

    return (<article className={`jobs-table-row ${job.status === 'error' ? 'has-error' : ''} ${job.status === 'canceled' ? 'is-canceled' : ''}`}>
        <div className="jobs-job-title">
            {cleanDisplayText(job.label)}
            {ownerName && <small className="jobs-owner">Created by {ownerName}</small>}
        </div>
        <div>
        <span className="job-status" style={{color: cfg.color}}>
          <i style={{background: cfg.color}}/>
            {cfg.label}
        </span>
        </div>
        <div className="jobs-cell-muted">{startedTime(job)}</div>
        <div className="jobs-cell-muted">{elapsed(job)}</div>
        <div className="jobs-cell-id" title={job.id}>{job.id}</div>
        {/*<div className="jobs-report-cell">*/}
        {/*    {canOpen ? (*/}
        {/*        <>*/}
        {/*            <button*/}
        {/*                className="jobs-report-link"*/}
        {/*                type="button"*/}
        {/*                onClick={() => onSelect(job)}*/}
        {/*            >*/}
        {/*                View Report*/}
        {/*            </button>*/}

        {/*            <button*/}
        {/*                className="jobs-report-link"*/}
        {/*                type="button"*/}
        {/*                onClick={() => onRerun(job)}*/}
        {/*            >*/}
        {/*                Run Again*/}
        {/*            </button>*/}
        {/*        </>*/}
        {/*    ) : (*/}
        {/*        <span className="job-running-note">Pending</span>*/}
        {/*    )}*/}
        {/*</div>*/}
        <div className="jobs-actions">
            {canOpen && (
                <>
                    <button
                        className="jobs-icon-btn expand-on-hover"
                        data-label="view-report"
                        onClick={() => onSelect(job)}
                    >
                        <span className="icon">📄</span>
                        <span className="label">View report</span>
                    </button>

                    <button
                        className="jobs-icon-btn expand-on-hover"
                        data-label="run-again"
                        onClick={() => onRerun(job)}
                    >
                        <span className="icon">↻</span>
                        <span className="label">Run again</span>
                    </button>
                </>
            )}

            {job.status === 'running' && (
                <button
                    className="jobs-icon-btn danger always-labeled"
                    onClick={() => onCancel(job)}
                >
                    <span className="icon">✕</span>
                    <span className="label">Cancel</span>
                </button>
            )}
            {job.status === 'canceled' && (
                <>
                    <button
                        className="jobs-icon-btn expand-on-hover"
                        data-label="run-again"
                        onClick={() => onRerun(job)}
                    >
                        <span className="icon">↻</span>
                        <span className="label">Run again</span>
                    </button>
                </>
            )}
        </div>
        {job.status === 'error' && job.error && (<div className="job-error">{job.error}</div>)}
    </article>)
}
