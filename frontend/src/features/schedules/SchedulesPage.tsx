import { useEffect, useState, type FormEvent } from 'react'
import {
  CalendarClockIcon,
  CircleAlertIcon,
  CircleCheckIcon,
  CircleHelpIcon,
  CircleXIcon,
  FileTextIcon,
  LoaderCircleIcon,
  PencilIcon,
  PlusIcon,
  Trash2Icon,
} from 'lucide-react'
import { ApiError } from '../../api/client'
import type { AgentScheduledJob, AgentScheduledJobWrite } from '../../api/contracts'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldSet,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useScheduledJobs } from './useScheduledJobs'
import { mockScheduleRun } from './mockScheduleRun'

const emptyForm: AgentScheduledJobWrite = {
  title: '',
  instruction: '',
  cronExpression: '0 6 * * *',
}

const createdAtFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const exactTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'medium',
})

function formatCreatedAt(createdAt: string) {
  const date = new Date(createdAt)
  return Number.isNaN(date.getTime()) ? 'Unknown' : createdAtFormatter.format(date)
}

function formatExactTime(value: string | null) {
  if (!value) return 'Not available'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown' : exactTimeFormatter.format(date)
}

function formatDuration(durationMs: number) {
  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000))
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (days > 0) return `${days}d ${hours}h ${minutes}m`
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

function formatNextRun(nextRunAt: string | null, now: number) {
  if (!nextRunAt) return 'Not scheduled'
  const nextRun = new Date(nextRunAt)
  if (Number.isNaN(nextRun.getTime())) return 'Unknown'
  const remaining = nextRun.getTime() - now
  return remaining <= 0 ? 'Starting now' : `in ${formatDuration(remaining)}`
}

function ScheduleRunSummary({ job: schedule, now }: { job: AgentScheduledJob, now: number }) {
  const [referenceTime] = useState(() => Date.now())
  const job = { ...schedule, ...mockScheduleRun('never_run', referenceTime) }
  const runningFor = job.lastStartedAt
    ? formatDuration(now - new Date(job.lastStartedAt).getTime())
    : '0s'

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">Status</span>
        {job.lastStatus === 'running' && (
          <Badge variant="secondary"><LoaderCircleIcon data-icon="inline-start" />Running</Badge>
        )}
        {job.lastStatus === 'succeeded' && (
          <Badge><CircleCheckIcon data-icon="inline-start" />Succeeded</Badge>
        )}
        {job.lastStatus === 'failed' && (
          <Badge variant="destructive"><CircleXIcon data-icon="inline-start" />Failed</Badge>
        )}
        {job.lastStatus === 'never_run' && <Badge>Waiting</Badge>}
        {job.lastStatus === 'running' && (
          <span className="text-sm text-muted-foreground">Running for {runningFor}</span>
        )}
      </div>

      {job.lastStatus === 'running' && (
        <Skeleton
          className="h-2 w-full"
          role="progressbar"
          aria-label={`${job.title} is running`}
          aria-valuetext={`Running for ${runningFor}`}
        />
      )}

      <dl className="grid w-full gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-muted-foreground">Last completed</dt>
          <dd className="font-medium">{job.lastCompletedAt ? formatExactTime(job.lastCompletedAt) : 'Not completed yet'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Next run</dt>
          <dd className="font-medium">{formatNextRun(job.nextRunAt, now)}</dd>
          {job.nextRunAt && <dd className="text-muted-foreground">{formatExactTime(job.nextRunAt)}</dd>}
        </div>
      </dl>

      {job.lastStatus === 'failed' && job.lastError && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>Last run failed</AlertTitle>
          <AlertDescription>{job.lastError}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}

function errorMessage(cause: unknown, fallback: string) {
  if (cause instanceof ApiError && cause.status === 422) {
    return 'Check the schedule fields and cron expression, then try again.'
  }
  return cause instanceof Error ? cause.message : fallback
}

export function SchedulesPage() {
  const { jobs, status, error, create, update: updateJob, remove } = useScheduledJobs()
  const [now, setNow] = useState(() => Date.now())
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [actionError, setActionError] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [jobToInspect, setJobToInspect] = useState<AgentScheduledJob | null>(null)
  const [jobToEdit, setJobToEdit] = useState<AgentScheduledJob | null>(null)
  const [editForm, setEditForm] = useState<AgentScheduledJobWrite>({ title: '', instruction: '', cronExpression: '' })
  const [editError, setEditError] = useState('')
  const [isUpdating, setIsUpdating] = useState(false)
  const [jobToDelete, setJobToDelete] = useState<AgentScheduledJob | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  function openCreateDialog() {
    setFormError('')
    setCreateOpen(true)
  }

  function updateForm(field: keyof AgentScheduledJobWrite, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void createSchedule()
  }

  async function createSchedule() {
    const title = form.title.trim()
    const instruction = form.instruction.trim()
    const cronExpression = form.cronExpression.trim()
    if (!title || !instruction || !cronExpression) {
      setFormError('Complete all fields before creating this schedule.')
      return
    }

    setIsCreating(true)
    setFormError('')
    setActionError('')
    try {
      await create({ title, instruction, cronExpression })
      setForm(emptyForm)
      setCreateOpen(false)
    } catch (cause) {
      setFormError(errorMessage(cause, 'Unable to create the schedule.'))
    } finally {
      setIsCreating(false)
    }
  }

  function openEditDialog(job: AgentScheduledJob) {
    setJobToEdit(job)
    setEditForm({ title: job.title, instruction: job.instruction, cronExpression: job.cronExpression })
    setEditError('')
  }

  function submitScheduleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (jobToEdit) void saveSchedule(jobToEdit)
  }

  async function saveSchedule(job: AgentScheduledJob) {
    const title = editForm.title.trim()
    const instruction = editForm.instruction.trim()
    const cronExpression = editForm.cronExpression.trim()
    if (!title || !instruction || !cronExpression) {
      setEditError('Enter a title, instruction, and five-field cron expression.')
      return
    }

    setIsUpdating(true)
    setEditError('')
    setActionError('')
    try {
      await updateJob(job.id, { title, instruction, cronExpression })
      setJobToEdit(null)
    } catch (cause) {
      setEditError(errorMessage(cause, 'Unable to update the schedule.'))
    } finally {
      setIsUpdating(false)
    }
  }

  function confirmDelete() {
    if (jobToDelete) void deleteSchedule(jobToDelete)
  }

  async function deleteSchedule(job: AgentScheduledJob) {
    setIsDeleting(true)
    setActionError('')
    try {
      await remove(job.id)
      setJobToDelete(null)
    } catch (cause) {
      setActionError(errorMessage(cause, 'Unable to delete the schedule.'))
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-6 pb-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">Schedules</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Recurring instructions for the Leafy agent.
          </p>
        </div>
        <Button type="button" onClick={openCreateDialog}>
          <PlusIcon data-icon="inline-start" />
          New schedule
        </Button>
      </header>

      {(error || actionError) && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>Schedule action failed</AlertTitle>
          <AlertDescription>{actionError || error}</AlertDescription>
        </Alert>
      )}

      {status === 'loading' ? (
        <Card>
          <CardHeader>
            <CardTitle>Current schedules</CardTitle>
            <CardDescription>Loading agent schedules.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      ) : jobs.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <CalendarClockIcon />
            </EmptyMedia>
            <EmptyTitle>No agent schedules</EmptyTitle>
            <EmptyDescription>Create a recurring instruction to run the agent automatically.</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button type="button" onClick={openCreateDialog}>
              <PlusIcon data-icon="inline-start" />
              New schedule
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <section aria-labelledby="current-schedules" className="flex flex-col gap-3">
          <div>
            <h2 id="current-schedules" className="text-base font-medium">Current schedules</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {jobs.length} scheduled agent {jobs.length === 1 ? 'run' : 'runs'}
            </p>
          </div>
          <div className="grid gap-3">
            {jobs.map((job) => (
              <Card key={job.id} size="sm">
                <CardHeader>
                  <CardTitle className="truncate pr-2" title={job.title}>{job.title}</CardTitle>
                  <CardDescription>Created {formatCreatedAt(job.createdAt)}</CardDescription>
                  <CardAction className="flex items-center gap-1.5">
                    <Badge variant="outline" className="max-w-36 font-mono font-normal" title={job.cronExpression}>
                      {job.cronExpression}
                    </Badge>
                      <Button
                        type="button"
                        variant="destructive"
                        size="icon-sm"
                        aria-label={`Delete ${job.title}`}
                        title={`Delete ${job.title}`}
                        onClick={() => setJobToDelete(job)}
                      >
                        <Trash2Icon />
                      </Button>
                  </CardAction>
                </CardHeader>
                <CardContent className="flex flex-col items-start gap-3">
                  <p className="line-clamp-3 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                    {job.instruction}
                  </p>
                  <ScheduleRunSummary job={job} now={now} />
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => setJobToInspect(job)}>
                      <FileTextIcon data-icon="inline-start" />
                      View instruction
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={() => openEditDialog(job)}>
                      <PencilIcon data-icon="inline-start" />
                      Edit schedule
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      <Dialog open={createOpen} onOpenChange={(open) => { if (!isCreating) setCreateOpen(open) }}>
        <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>New agent schedule</DialogTitle>
            <DialogDescription>Choose when the agent should run this instruction.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submitCreate}>
            <FieldSet disabled={isCreating}>
              <FieldGroup>
                <Field>
                  <div className="flex items-center gap-1">
                    <FieldLabel htmlFor="schedule-title">Title</FieldLabel>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button type="button" variant="ghost" size="icon-xs" aria-label="About the schedule title">
                          <CircleHelpIcon />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="right">Used to identify this schedule in the list.</TooltipContent>
                    </Tooltip>
                  </div>
                  <Input
                    id="schedule-title"
                    required
                    placeholder="Morning crop status report"
                    value={form.title}
                    onChange={(event) => updateForm('title', event.target.value)}
                  />
                  <FieldDescription>A quick summary of what the job does and when it runs.</FieldDescription>
                </Field>
                <Field>
                  <div className="flex items-center gap-1">
                    <FieldLabel htmlFor="schedule-instruction">Instruction</FieldLabel>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button type="button" variant="ghost" size="icon-xs" aria-label="About the schedule instruction">
                          <CircleHelpIcon />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="right">The agent receives this instruction every time the schedule runs.</TooltipContent>
                    </Tooltip>
                  </div>
                  <Textarea
                    id="schedule-instruction"
                    required
                    rows={5}
                    placeholder="Review the latest sensor readings. For any pH, EC, temperature, or water-level values outside their normal ranges, take the appropriate corrective action."
                    value={form.instruction}
                    onChange={(event) => updateForm('instruction', event.target.value)}
                  />
                  <FieldDescription>Tell the agent what to check, decide, or report when this schedule runs.</FieldDescription>
                </Field>
                <Field data-invalid={Boolean(formError)}>
                  <FieldLabel htmlFor="schedule-cron">Cron expression</FieldLabel>
                  <Input id="schedule-cron" required value={form.cronExpression} onChange={(event) => updateForm('cronExpression', event.target.value)} aria-invalid={Boolean(formError)} />
                  <FieldDescription>Use five fields, for example: 0 6 * * *</FieldDescription>
                  {formError && <FieldError>{formError}</FieldError>}
                </Field>
              </FieldGroup>
              <DialogFooter>
                <Button type="button" variant="outline" disabled={isCreating} onClick={() => setCreateOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={isCreating}>
                  <CalendarClockIcon data-icon="inline-start" />
                  {isCreating ? 'Creating…' : 'Create schedule'}
                </Button>
              </DialogFooter>
            </FieldSet>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={jobToEdit !== null} onOpenChange={(open) => { if (!open && !isUpdating) setJobToEdit(null) }}>
        <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit schedule</DialogTitle>
            <DialogDescription>Update the name, instruction, and timing for this job.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submitScheduleUpdate}>
            <FieldSet disabled={isUpdating}>
              <FieldGroup>
                <Field data-invalid={Boolean(editError)}>
                  <FieldLabel htmlFor="edit-schedule-title">Title</FieldLabel>
                  <Input
                    id="edit-schedule-title"
                    required
                    value={editForm.title}
                    onChange={(event) => setEditForm((current) => ({ ...current, title: event.target.value }))}
                    aria-invalid={Boolean(editError)}
                  />
                </Field>
                <Field data-invalid={Boolean(editError)}>
                  <FieldLabel htmlFor="edit-schedule-instruction">Instruction</FieldLabel>
                  <Textarea
                    id="edit-schedule-instruction"
                    required
                    rows={7}
                    value={editForm.instruction}
                    onChange={(event) => setEditForm((current) => ({ ...current, instruction: event.target.value }))}
                    aria-invalid={Boolean(editError)}
                  />
                  <FieldDescription>Tell the agent what to check, decide, or report when this schedule runs.</FieldDescription>
                </Field>
                <Field data-invalid={Boolean(editError)}>
                  <FieldLabel htmlFor="edit-schedule-cron">Cron expression</FieldLabel>
                  <Input
                    id="edit-schedule-cron"
                    required
                    value={editForm.cronExpression}
                    onChange={(event) => setEditForm((current) => ({ ...current, cronExpression: event.target.value }))}
                    aria-invalid={Boolean(editError)}
                  />
                  <FieldDescription>Use five fields, for example: 0 6 * * *</FieldDescription>
                  {editError && <FieldError>{editError}</FieldError>}
                </Field>
              </FieldGroup>
              <DialogFooter>
                <Button type="button" variant="outline" disabled={isUpdating} onClick={() => setJobToEdit(null)}>Cancel</Button>
                <Button type="submit" disabled={isUpdating}>
                  <PencilIcon data-icon="inline-start" />
                  {isUpdating ? 'Saving…' : 'Save changes'}
                </Button>
              </DialogFooter>
            </FieldSet>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={jobToInspect !== null} onOpenChange={(open) => { if (!open) setJobToInspect(null) }}>
        <DialogContent className="max-h-[90svh] sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{jobToInspect?.title ?? 'Schedule instruction'}</DialogTitle>
            <DialogDescription>
              {jobToInspect ? `Runs on ${jobToInspect.cronExpression}.` : ''}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60svh] overflow-y-auto rounded-lg border bg-muted/40 p-3">
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{jobToInspect?.instruction}</p>
          </div>
          <DialogFooter>
            <Button type="button" onClick={() => setJobToInspect(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={jobToDelete !== null} onOpenChange={(open) => { if (!open && !isDeleting) setJobToDelete(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this schedule?</DialogTitle>
            <DialogDescription>
              {jobToDelete ? `“${jobToDelete.title}” will no longer trigger agent runs.` : ''}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" disabled={isDeleting} onClick={() => setJobToDelete(null)}>Cancel</Button>
            <Button type="button" variant="destructive" disabled={isDeleting} onClick={confirmDelete}>
              <Trash2Icon data-icon="inline-start" />
              {isDeleting ? 'Deleting…' : 'Delete schedule'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
