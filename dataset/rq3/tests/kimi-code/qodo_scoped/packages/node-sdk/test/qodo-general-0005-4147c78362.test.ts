import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';

import { afterEach, describe, expect, it } from 'vitest';

import { createKimiHarness, type Event, type KimiError } from '#/index';

import { makeTempDir, removeTempDirs } from './session-runtime-helpers';
import { TEST_IDENTITY } from './test-identity';
import { SDKRpcClientBase } from '#/rpc';

const tempDirs: string[] = [];

afterEach(async () => {
  await removeTempDirs(tempDirs);
});

describe('Session plan, compact, usage, and resume APIs', () => {
  it('sets plan mode through manualEnterPlan and clears the active plan file', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-plan-home-');
    const workDir = await makeTempDir(tempDirs, 'kimi-sdk-plan-work-');
    await writeTestConfig(homeDir);
    const harness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });

    try {
      const session = await harness.createSession({ id: 'ses_plan_runtime', workDir });

      const planOn = waitForSessionEvent(
        session,
        (event) => event.type === 'agent.status.updated' && event.planMode === true,
      );
      await session.setPlanMode(true);
      await expect(planOn).resolves.toMatchObject({
        type: 'agent.status.updated',
        planMode: true,
      });

      await expect(session.clearPlan()).resolves.toBeUndefined();
      await expect(session.getPlan()).resolves.toMatchObject({
        content: '',
      });
      await session.cancel();

      const planOff = waitForSessionEvent(
        session,
        (event) => event.type === 'agent.status.updated' && event.planMode === false,
      );
      await session.setPlanMode(false);
      await expect(planOff).resolves.toMatchObject({
        type: 'agent.status.updated',
        planMode: false,
      });
    } finally {
      await harness.close();
    }
  });

  it('prepares the plans directory without creating plan files on repeated toggles', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-plan-toggle-home-');
    const workDir = await makeTempDir(tempDirs, 'kimi-sdk-plan-toggle-work-');
    await writeTestConfig(homeDir);
    const harness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });

    try {
      const session = await harness.createSession({ id: 'ses_plan_toggle_runtime', workDir });

      await session.setPlanMode(true);
      const firstPlan = await session.getPlan();
      if (firstPlan === null) throw new Error('expected first plan');
      const plansDir = dirname(firstPlan.path);
      await expect(markdownFiles(plansDir)).resolves.toEqual([]);

      await session.setPlanMode(false);
      await session.setPlanMode(true);
      const secondPlan = await session.getPlan();
      if (secondPlan === null) throw new Error('expected second plan');

      expect(secondPlan.path).not.toBe(firstPlan.path);
      expect(dirname(secondPlan.path)).toBe(plansDir);
      await expect(markdownFiles(plansDir)).resolves.toEqual([]);
    } finally {
      await harness.close();
    }
  });

  it('rejects manual compaction on an empty session with compaction.unable', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-compact-home-');
    const workDir = await makeTempDir(tempDirs, 'kimi-sdk-compact-work-');
    await writeTestConfig(homeDir);
    const harness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });

    try {
      const session = await harness.createSession({ id: 'ses_compact_runtime', workDir });

      await expect(session.compact({ instruction: 'Keep important facts.' })).rejects.toMatchObject({
        name: 'KimiError',
        code: 'compaction.unable',
      } satisfies Partial<KimiError>);
    } finally {
      await harness.close();
    }
  });

  it('returns current session usage totals', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-usage-home-');
    const workDir = await makeTempDir(tempDirs, 'kimi-sdk-usage-work-');
    await writeTestConfig(homeDir);
    const harness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });

    try {
      const session = await harness.createSession({ id: 'ses_usage_runtime', workDir });

      await expect(session.getUsage()).resolves.toEqual({});
    } finally {
      await harness.close();
    }
  });

  it('resumes a persisted session and restores runtime plan mode from wire history', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-resume-home-');
    const workDir = await makeTempDir(tempDirs, 'kimi-sdk-resume-work-');
    await writeTestConfig(homeDir);
    const harness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });

    try {
      const created = await harness.createSession({
        id: 'ses_resume_runtime',
        workDir,
        model: 'test-model',
      });
      await created.setPlanMode(true);
      await expect(created.getPlan()).resolves.toMatchObject({
        content: '',
      });
      await created.close();
      expect(harness.getSession(created.id)).toBeUndefined();

      const resumed = await harness.resumeSession({ id: created.id });

      expect(resumed.id).toBe(created.id);
      expect(resumed.workDir).toBe(workDir);
      await expect(resumed.getStatus()).resolves.toMatchObject({
        model: 'test-model',
        planMode: true,
      });
      await expect(resumed.getPlan()).resolves.toMatchObject({
        content: '',
        path: expect.stringContaining('/plans/'),
      });
      expect(harness.getSession(created.id)).toBe(resumed);
    } finally {
      await harness.close();
    }
  });

  it.todo('marks resumed plan mode active when the restored plan has no plan data', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-resume-legacy-plan-home-');
    const workDir = await makeTempDir(tempDirs, 'kimi-sdk-resume-legacy-plan-work-');
    await writeTestConfig(homeDir);
    const createdHarness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });
    let sessionId = '';
    let sessionDir = '';

    try {
      const created = await createdHarness.createSession({
        id: 'ses_resume_legacy_plan_runtime',
        workDir,
        model: 'test-model',
      });
      await created.setPlanMode(true);
      const summary = created.summary;
      expect(summary).toBeDefined();
      sessionId = created.id;
      sessionDir = summary!.sessionDir;
    } finally {
      await createdHarness.close();
    }

    await removeManualPlanIds(sessionDir);

    const resumedHarness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });
    try {
      const resumed = await resumedHarness.resumeSession({ id: sessionId });

      await expect(resumed.getStatus()).resolves.toMatchObject({
        planMode: true,
      });
      await expect(resumed.getPlan()).resolves.toBeNull();
    } finally {
      await resumedHarness.close();
    }
  });

  it('forks a session, drops goal state, and returns an active fork session', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-fork-home-');
    const workDir = await makeTempDir(tempDirs, 'kimi-sdk-fork-work-');
    await writeTestConfig(homeDir);
    const harness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });

    try {
      const source = await harness.createSession({
        id: 'ses_fork_runtime_source',
        workDir,
        model: 'test-model',
        metadata: {
          source: true,
          goal: {
            goalId: 'source-goal',
            objective: 'source objective',
            status: 'active',
            turnsUsed: 0,
            tokensUsed: 0,
            budgetLimits: {},
          },
        },
      });
      await source.createGoal({ objective: 'source objective' });
      await source.setPlanMode(true);
      const sourcePlan = await source.getPlan();
      if (sourcePlan === null) throw new Error('expected source plan');
      await mkdir(dirname(sourcePlan.path), { recursive: true });
      await writeFile(sourcePlan.path, 'source plan', 'utf-8');

      const fork = await harness.forkSession({
        id: source.id,
        forkId: 'ses_fork_runtime_child',
        title: 'Forked runtime',
        metadata: {
          child: true,
          goal: {
            goalId: 'metadata-goal',
            objective: 'metadata objective',
            status: 'active',
            turnsUsed: 0,
            tokensUsed: 0,
            budgetLimits: {},
          },
        },
      });

      expect(fork.id).toBe('ses_fork_runtime_child');
      expect(fork.workDir).toBe(workDir);
      await expect(fork.getStatus()).resolves.toMatchObject({ model: 'test-model' });
      expect(harness.getSession(fork.id)).toBe(fork);
      await expect(fork.getUsage()).resolves.toEqual({});

      const forkSummary = fork.summary;
      expect(forkSummary).toBeDefined();
      const forkPlan = await fork.getPlan();
      expect(forkPlan).toEqual({
        id: sourcePlan.id,
        content: 'source plan',
        path: join(forkSummary!.sessionDir, 'agents', 'main', 'plans', `${sourcePlan.id}.md`),
      });
      expect(forkPlan?.path).not.toBe(sourcePlan.path);
      const forkWire = await readFile(
        join(forkSummary!.sessionDir, 'agents', 'main', 'wire.jsonl'),
        'utf-8',
      );
      const forkRecords = forkWire
        .trim()
        .split('\n')
        .map((line) => JSON.parse(line) as Record<string, unknown>);
      const enterRecord = forkRecords.find((record) => record['type'] === 'plan_mode.enter');
      expect(enterRecord).toEqual({
        type: 'plan_mode.enter',
        id: sourcePlan.id,
        time: expect.any(Number),
      });
      expect(forkRecords.find((record) => record['type'] === 'forked')).toEqual({
        type: 'forked',
        time: expect.any(Number),
      });
      expect(forkRecords.some((record) => record['type'] === 'goal.clear')).toBe(false);
      await expect(fork.getGoal()).resolves.toEqual({ goal: null });
      const forkState = JSON.parse(
        await readFile(join(forkSummary!.sessionDir, 'state.json'), 'utf-8'),
      ) as {
        title?: string;
        forkedFrom?: string;
        agents?: { main?: { homedir?: string } };
        custom?: Record<string, unknown>;
      };
      expect(forkState.title).toBe('Forked runtime');
      expect(forkState.forkedFrom).toBe(source.id);
      expect(forkState.agents?.main?.homedir).toBe(join(forkSummary!.sessionDir, 'agents', 'main'));
      expect(forkState.custom).toMatchObject({ source: true, child: true });
      expect(forkState.custom).not.toHaveProperty('goal');
    } finally {
      await harness.close();
    }
  });

  it('rejects an empty resume id', async () => {
    const homeDir = await makeTempDir(tempDirs, 'kimi-sdk-resume-empty-home-');
    const harness = createKimiHarness({ homeDir, identity: TEST_IDENTITY });

    try {
      await expect(harness.resumeSession({ id: '   ' })).rejects.toMatchObject({
        name: 'KimiError',
        code: 'session.id_empty',
      } satisfies Partial<KimiError>);
    } finally {
      await harness.close();
    }
  });

  it('withInteractiveAgent sets agent id and plan/swarm/compact branches call appropriate RPCs', async () => {
    class FakeClient extends SDKRpcClientBase {
      public calls: Array<[string, any]> = [];
      protected async getRpc(): Promise<any> {
        const self = this;
        return {
          enterPlan: async (args: any) => {
            self.calls.push(['enterPlan', args]);
          },
          cancelPlan: async (args: any) => {
            self.calls.push(['cancelPlan', args]);
          },
          enterSwarm: async (args: any) => {
            self.calls.push(['enterSwarm', args]);
          },
          exitSwarm: async (args: any) => {
            self.calls.push(['exitSwarm', args]);
          },
          beginCompaction: async (args: any) => {
            self.calls.push(['beginCompaction', args]);
          },
        };
      }
    }
  
    const client = new FakeClient();
  
    // Default agent id (not inside withInteractiveAgent) should be 'main'
    await client.setPlanMode({ sessionId: 'sess-p', enabled: true } as any);
    let call = client.calls.find((c) => c[0] === 'enterPlan');
    expect(call).toBeDefined();
    expect(call![1].agentId).toBe('main');
  
    // Use withInteractiveAgent to execute a cancellation with a different agent id
    await client.withInteractiveAgent('agent-42', () =>
      client.setPlanMode({ sessionId: 'sess-p', enabled: false } as any),
    );
    call = client.calls.find((c) => c[0] === 'cancelPlan' && c[1].agentId === 'agent-42');
    expect(call).toBeDefined();
  
    // enterSwarm when enabled=true uses enterSwarm
    await client.withInteractiveAgent('a9', () =>
      client.setSwarmMode({ sessionId: 'sess-s', enabled: true, trigger: 'task' } as any),
    );
    const enterSwarmCall = client.calls.find((c) => c[0] === 'enterSwarm');
    expect(enterSwarmCall).toBeDefined();
    expect(enterSwarmCall![1].agentId).toBe('a9');
    expect(enterSwarmCall![1].trigger).toBe('task');
  
    // exitSwarm when enabled=false uses exitSwarm
    await client.withInteractiveAgent('a10', () =>
      client.setSwarmMode({ sessionId: 'sess-s', enabled: false } as any),
    );
    const exitSwarmCall = client.calls.find((c) => c[0] === 'exitSwarm' && c[1].agentId === 'a10');
    expect(exitSwarmCall).toBeDefined();
  
    // compact includes instruction when provided
    await client.compact({ sessionId: 'sess-c', instruction: 'keep only key facts' } as any);
    const compactCall = client.calls.find((c) => c[0] === 'beginCompaction' && c[1].sessionId === 'sess-c');
    expect(compactCall).toBeDefined();
    expect(compactCall![1]).toMatchObject({ instruction: 'keep only key facts' });
  
    // compact without instruction should still call beginCompaction but not include instruction
    await client.compact({ sessionId: 'sess-c2' } as any);
    const compactCall2 = client.calls.find((c) => c[0] === 'beginCompaction' && c[1].sessionId === 'sess-c2');
    expect(compactCall2).toBeDefined();
    expect(Object.prototype.hasOwnProperty.call(compactCall2![1], 'instruction')).toBe(false);
  });


  it('question handler returns null if missing, returns value if present, and handles throws', async () => {
    class FakeClient extends SDKRpcClientBase {
      protected async getRpc(): Promise<any> {
        return {} as any;
      }
    }
    const client = new FakeClient();
  
    // No handler -> null
    const noHandler = await client.requestQuestion({
      sessionId: 'q-sess',
      agentId: 'q-agent',
      question: 'Is anyone there?',
    });
    expect(noHandler).toBeNull();
  
    // Working handler -> returns result
    client.setQuestionHandler('q-sess', async (req) => {
      expect(req.sessionId).toBe('q-sess');
      expect(req.agentId).toBe('q-agent');
      return { answer: 'yes' };
    });
    const success = await client.requestQuestion({
      sessionId: 'q-sess',
      agentId: 'q-agent',
      question: 'Is anyone there?',
    });
    expect(success).toEqual({ answer: 'yes' });
  
    // Throwing handler -> emits error and returns null
    const events: Event[] = [];
    client.onEvent((e) => events.push(e));
    client.setQuestionHandler('q-sess', async () => {
      throw 'unexpected';
    });
    const thrown = await client.requestQuestion({
      sessionId: 'q-sess',
      agentId: 'q-agent',
      question: 'Will this throw?',
    });
    expect(thrown).toBeNull();
    const errEvent = events.find((e) => e.type === 'error' && e.sessionId === 'q-sess');
    expect(errEvent).toBeDefined();
    expect(errEvent?.agentId).toBe('q-agent');
  });


  it('emits error event and returns cancelled when approval handler throws', async () => {
    class FakeClient extends SDKRpcClientBase {
      protected async getRpc(): Promise<any> {
        return {} as any;
      }
    }
    const client = new FakeClient();
  
    const received: Event[] = [];
    client.onEvent((e) => received.push(e));
  
    client.setApprovalHandler('sess-err', async () => {
      throw new Error('handler failed');
    });
  
    const resp = await client.requestApproval({
      sessionId: 'sess-err',
      agentId: 'agent-err',
      name: 'boom',
      description: 'should throw',
    });
  
    expect(resp).toEqual({
      decision: 'cancelled',
      feedback: 'Approval handler failed.',
    });
  
    // One error event should have been emitted with matching session/agent
    expect(received.length).toBeGreaterThanOrEqual(1);
    const err = received.find((e) => e.type === 'error' && e.sessionId === 'sess-err');
    expect(err).toBeDefined();
    expect(err?.agentId).toBe('agent-err');
  });


  it('approval handler returns default cancelled when missing and forwards handler result when present', async () => {
    class FakeClient extends SDKRpcClientBase {
      protected async getRpc(): Promise<any> {
        return {} as any;
      }
    }
    const client = new FakeClient();
  
    // No handler -> default cancelled response
    const defaultResp = await client.requestApproval({
      sessionId: 'sess-default',
      agentId: 'agent-default',
      name: 'approve-test',
      description: 'no handler',
    });
    expect(defaultResp).toEqual({
      decision: 'cancelled',
      feedback: 'No approval handler registered.',
    });
  
    // Install handler -> response should be returned
    client.setApprovalHandler('sess-default', async (req) => {
      expect(req.sessionId).toBe('sess-default');
      expect(req.agentId).toBe('agent-default');
      return { decision: 'approved', feedback: 'ok' };
    });
  
    const handledResp = await client.requestApproval({
      sessionId: 'sess-default',
      agentId: 'agent-default',
      name: 'approve-test',
      description: 'with handler',
    });
    expect(handledResp).toEqual({ decision: 'approved', feedback: 'ok' });
  });

});

async function removeManualPlanIds(sessionDir: string): Promise<void> {
  const wirePath = join(sessionDir, 'agents', 'main', 'wire.jsonl');
  const raw = await readFile(wirePath, 'utf-8');
  const lines = raw
    .split('\n')
    .filter((line) => line.length > 0)
    .flatMap((line) => {
      const record = JSON.parse(line) as Record<string, unknown>;
      if (record['type'] === 'plan.enter') return [];
      if (record['type'] === 'plan.manual_enter') delete record['id'];
      return [JSON.stringify(record)];
    });
  await writeFile(wirePath, `${lines.join('\n')}\n`, 'utf-8');
}

function waitForSessionEvent(
  session: { onEvent(listener: (event: Event) => void): () => void },
  predicate: (event: Event) => boolean,
): Promise<Event> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      unsubscribe();
      reject(new Error('Timed out waiting for session event'));
    }, 1_000);
    const unsubscribe = session.onEvent((event) => {
      if (!predicate(event)) return;
      clearTimeout(timeout);
      unsubscribe();
      resolve(event);
    });
  });
}

async function writeTestConfig(homeDir: string): Promise<void> {
  await writeFile(
    join(homeDir, 'config.toml'),
    `
default_model = "test-model"

[providers.local]
type = "openai"
base_url = "https://example.test/v1"
api_key = "sk-test"

[models.test-model]
provider = "local"
model = "test-model"
max_context_size = 200000
`,
    'utf-8',
  );
}

async function markdownFiles(dir: string): Promise<string[]> {
  const entries = await readdir(dir);
  return entries.filter((entry) => entry.endsWith('.md')).toSorted();
}
