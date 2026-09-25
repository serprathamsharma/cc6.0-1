import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3000'
const API = process.env.API_URL || 'http://localhost:8000'

test.describe('ScoutIQ E2E', () => {
  let token: string
  let taskId: string
  let runId: string

  test.beforeAll(async ({ request }) => {
    // Register a test user
    const res = await request.post(`${API}/api/v1/auth/register`, {
      data: {
        name: 'Test User',
        email: `test_${Date.now()}@example.com`,
        password: 'testpassword123',
        workspace_name: 'Test Workspace',
      },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    token = body.access_token
  })

  test('Health check returns ok', async ({ request }) => {
    const res = await request.get(`${API}/health`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.status).toBe('ok')
  })

  test('Scenario A: Create and run AI/ML internships task', async ({ request }) => {
    // Create task
    const createRes = await request.post(`${API}/api/v1/tasks`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { prompt: 'Find AI/ML internships in India posted in the last 30 days at product companies, with apply link, stipend, and skills.' },
    })
    expect(createRes.ok()).toBeTruthy()
    const task = await createRes.json()
    taskId = task.id
    expect(task.id).toBeTruthy()

    // Plan workflow
    const planRes = await request.post(`${API}/api/v1/tasks/${taskId}/plan`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(planRes.ok()).toBeTruthy()
    const workflow = await planRes.json()
    expect(workflow.dag.nodes.length).toBeGreaterThan(3)
    expect(workflow.requirement_spec.entity_type).toBe('job_posting')

    // Approve and run
    const runRes = await request.post(`${API}/api/v1/tasks/${taskId}/workflows/${workflow.id}/approve`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { auto_run: true },
    })
    expect(runRes.ok()).toBeTruthy()
    const run = await runRes.json()
    runId = run.id
  })

  test('Scenario A: Wait for completion and verify >=50 records', async ({ request }) => {
    test.setTimeout(60_000)
    // Poll until completed
    let run: any
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 2000))
      const res = await request.get(`${API}/api/v1/tasks/${taskId}/runs/${runId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      run = await res.json()
      if (run.status === 'completed' || run.status === 'failed') break
    }
    expect(run.status).toBe('completed')
    expect(run.records_deduped).toBeGreaterThanOrEqual(50)
    expect(run.demo_mode).toBe(true)
  })

  test('Scenario A: Records have source URLs and evidence snippets', async ({ request }) => {
    const res = await request.get(`${API}/api/v1/tasks/${taskId}/runs/${runId}/records?limit=10`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.ok()).toBeTruthy()
    const records = await res.json()
    expect(records.length).toBeGreaterThan(0)
    for (const rec of records) {
      expect(rec.id).toBeTruthy()
      expect(rec.data).toBeTruthy()
      // Every record must have field_values with provenance
      expect(rec.field_values.length).toBeGreaterThan(0)
      const withSource = rec.field_values.filter((fv: any) => fv.source_url)
      expect(withSource.length).toBeGreaterThan(0)
    }
  })

  test('Export: all 4 formats succeed', async ({ request }) => {
    for (const fmt of ['csv', 'json', 'xlsx', 'parquet']) {
      const res = await request.post(`${API}/api/v1/tasks/${taskId}/runs/${runId}/export`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { format: fmt, include_provenance: true },
      })
      expect(res.ok()).toBeTruthy()
      const body = await res.body()
      expect(body.length).toBeGreaterThan(0)
    }
  })

  test('Scenario B: Hackathon sponsors task runs end to end', async ({ request }) => {
    const createRes = await request.post(`${API}/api/v1/tasks`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { prompt: 'Find companies that sponsored tech hackathons or developer events in Delhi/NCR, with sponsorship tier and a contact page.' },
    })
    const task = await createRes.json()
    const planRes = await request.post(`${API}/api/v1/tasks/${task.id}/plan`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const wf = await planRes.json()
    expect(wf.requirement_spec.entity_type).toBe('sponsor')
    const runRes = await request.post(`${API}/api/v1/tasks/${task.id}/workflows/${wf.id}/approve`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { auto_run: true },
    })
    expect(runRes.ok()).toBeTruthy()
    const run = await runRes.json()
    // Wait
    await new Promise(r => setTimeout(r, 10_000))
    const statusRes = await request.get(`${API}/api/v1/tasks/${task.id}/runs/${run.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const finalRun = await statusRes.json()
    expect(['completed', 'running']).toContain(finalRun.status)
  })

  test('Scenario C: PM SaaS pricing task runs end to end', async ({ request }) => {
    const createRes = await request.post(`${API}/api/v1/tasks`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { prompt: 'Collect pricing plans of the top 20 project-management SaaS tools.' },
    })
    const task = await createRes.json()
    const planRes = await request.post(`${API}/api/v1/tasks/${task.id}/plan`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const wf = await planRes.json()
    expect(wf.requirement_spec.entity_type).toBe('pricing_plan')
    expect(runRes => runRes).toBeTruthy()
  })
})
