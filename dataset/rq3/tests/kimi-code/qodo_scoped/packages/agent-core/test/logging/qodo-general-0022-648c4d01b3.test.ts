import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  __resetRootLoggerForTest,
  getRootLogger,
  log,
  redact,
  resolveGlobalLogPath,
} from '#/logging/logger';
import { flushDiagnosticLogs } from '#/logging/logger';

let homeDir: string;

beforeEach(async () => {
  await __resetRootLoggerForTest();
  homeDir = await mkdtemp(join(tmpdir(), 'logger-test-'));
});

afterEach(async () => {
  await __resetRootLoggerForTest();
  await rm(homeDir, { recursive: true, force: true });
});

function defaultConfig(level: 'info' | 'debug' | 'warn' | 'error' | 'off' = 'info') {
  return {
    level,
    globalLogPath: resolveGlobalLogPath(homeDir),
    globalMaxBytes: 1_000_000,
    globalFiles: 3,
    sessionMaxBytes: 500_000,
    sessionFiles: 2,
  } as const;
}

async function readGlobal(): Promise<string> {
  return readGlobalAt(homeDir);
}

async function readGlobalAt(dir: string): Promise<string> {
  try {
    return await readFile(resolveGlobalLogPath(dir), 'utf-8');
  } catch {
    return '';
  }
}

describe('log — pre-configure noop', () => {
  it('silently swallows calls before configure', async () => {
    expect(() => {
      log.info('before configure');
    }).not.toThrow();
    expect(await readGlobal()).toBe('');
  });

  it('the same `log` import routes to sink after configure (late-binding)', async () => {
    log.info('pre-config'); // dropped
    await getRootLogger().configure(defaultConfig());
    log.info('post-config');
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).not.toContain('pre-config');
    expect(text).toContain('post-config');
  });
});

describe('configure idempotency', () => {
  it('second configure with deep-equal config is a no-op', async () => {
    await getRootLogger().configure(defaultConfig());
    log.info('one');
    await getRootLogger().flush();
    await getRootLogger().configure(defaultConfig());
    log.info('two');
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toContain('one');
    expect(text).toContain('two');
  });

  it('does not throw on multiple harness-like configure cycles', async () => {
    for (let i = 0; i < 3; i++) {
      await getRootLogger().configure(defaultConfig());
    }
    expect(getRootLogger().isConfigured()).toBe(true);
  });

  it('reconfigures the global sink when config changes', async () => {
    await getRootLogger().configure(defaultConfig('info'));
    const nextHomeDir = await mkdtemp(join(tmpdir(), 'logger-next-home-'));
    try {
      await getRootLogger().configure({
        ...defaultConfig('debug'),
        globalLogPath: resolveGlobalLogPath(nextHomeDir),
      });
      log.debug('after-reconfigure');
      await getRootLogger().flushGlobal();
      expect(await readGlobal()).not.toContain('after-reconfigure');
      expect(await readGlobalAt(nextHomeDir)).toContain('after-reconfigure');
    } finally {
      await rm(nextHomeDir, { recursive: true, force: true });
    }
  });
});

describe('level filtering', () => {
  it('drops entries below configured level', async () => {
    await getRootLogger().configure(defaultConfig('warn'));
    log.info('info-line');
    log.warn('warn-line');
    log.error('error-line');
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).not.toContain('info-line');
    expect(text).toContain('warn-line');
    expect(text).toContain('error-line');
  });

  it('off level disables all output', async () => {
    await getRootLogger().configure(defaultConfig('off'));
    log.error('should-not-write');
    await getRootLogger().flush();
    expect(await readGlobal()).toBe('');
  });
});

describe('payload shapes', () => {
  it('accepts Error directly (no manual wrap needed)', async () => {
    await getRootLogger().configure(defaultConfig());
    const err = new Error('boom');
    log.error('provider failed', err);
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toContain('provider failed');
    expect(text).toMatch(/Error: boom/);
  });

  it('accepts plain object as ctx', async () => {
    await getRootLogger().configure(defaultConfig());
    log.info('hello', { sessionId: 'ses_x', model: 'kimi-k2' });
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toContain('sessionId=ses_x');
    expect(text).toContain('model=kimi-k2');
  });

  it('bunyan-style: ctx with `error: Error` field hoists stack out', async () => {
    await getRootLogger().configure(defaultConfig());
    const err = new Error('persist failed');
    log.error('wire persist failed', { agentHomedir: '/tmp/a', error: err });
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toContain('agentHomedir=/tmp/a');
    expect(text).toMatch(/Error: persist failed/);
  });

  it('coerces primitive payload into a reason field', async () => {
    await getRootLogger().configure(defaultConfig());
    log.warn('weird path', 'oh no');
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toContain('reason="oh no"');
  });

  it('accepts a `catch (e: unknown)` binding without wrapping', async () => {
    await getRootLogger().configure(defaultConfig());
    try {
      throw new Error('caught');
    } catch (error) {
      log.error('caught it', error);
    }
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toMatch(/Error: caught/);
  });

  it('does not let throwing payload accessors escape into caller flow', async () => {
    await getRootLogger().configure(defaultConfig());
    const payload = new Proxy(
      {},
      {
        get() {
          throw new Error('getter boom');
        },
        ownKeys() {
          return ['error'];
        },
        getOwnPropertyDescriptor() {
          return { configurable: true, enumerable: true };
        },
      },
    );

    expect(() => {
      log.warn('proxy payload', payload);
    }).not.toThrow();
    await getRootLogger().flush();
    expect(await readGlobal()).not.toContain('proxy payload');
  });
});

describe('createChild', () => {
  it('binds ctx that travels with every entry', async () => {
    await getRootLogger().configure(defaultConfig());
    const sessionLog = log.createChild({ sessionId: 'ses_a', model: 'kimi-k2' });
    sessionLog.info('first');
    sessionLog.warn('second', { extra: 'x' });
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toMatch(/first.*sessionId=ses_a.*model=kimi-k2/);
    expect(text).toMatch(/second.*extra=x.*sessionId=ses_a/);
  });

  it('chains: parent ctx + child ctx + call ctx all merged', async () => {
    await getRootLogger().configure(defaultConfig());
    const sessionLog = log.createChild({ sessionId: 'ses_a' });
    const agentLog = sessionLog.createChild({ agentId: 'main' });
    agentLog.info('turn started', { turnId: 7 });
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toContain('sessionId=ses_a');
    expect(text).toContain('agentId=main');
    expect(text).toContain('turnId=7');
  });

  it('bound ctx overrides call-site ctx (cannot accidentally overwrite ownership)', async () => {
    await getRootLogger().configure(defaultConfig());
    const sessionLog = log.createChild({ sessionId: 'ses_a' });
    sessionLog.info('msg', { sessionId: 'ses_FAKE', extra: 'k' });
    await getRootLogger().flush();
    const text = await readGlobal();
    expect(text).toContain('sessionId=ses_a');
    expect(text).not.toContain('ses_FAKE');
    expect(text).toContain('extra=k');
  });
});

describe('session routing', () => {
  it('writes sessionId-tagged entries to session sink only', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const handle = getRootLogger().attachSession({ sessionId: 'ses_abc', sessionDir });
      const sessionLog = log.createChild({ sessionId: 'ses_abc' });
      sessionLog.info('hello');
      await handle.flush();
      await getRootLogger().flush();
      const global = await readGlobal();
      const session = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(global).not.toContain('hello');
      expect(session).toContain('hello');
      await handle.close();
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });

  it('omits stable main-agent fields from all session lines with agentId=main', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const handle = getRootLogger().attachSession({ sessionId: 'ses_abc', sessionDir });
      const sessionLog = handle.logger.createChild({ agentId: 'main' });
      sessionLog.info('llm config', { model: 'kimi-k2' });
      sessionLog.info('llm request', { turn: 0, step: 1 });
      await handle.flush();
      await getRootLogger().flush();

      const global = await readGlobal();
      expect(global).not.toMatch(/llm config/);
      expect(global).not.toMatch(/llm request/);

      const session = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(session).toMatch(/llm config(?!.*sessionId=ses_abc)/);
      expect(session).toMatch(/llm config(?!.*agentId=main)/);
      expect(session).toMatch(/llm request(?!.*sessionId=ses_abc)/);
      expect(session).toMatch(/llm request(?!.*agentId=main)/);
      await handle.close();
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });

  it('keeps subagent ids on session llm request lines', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const handle = getRootLogger().attachSession({ sessionId: 'ses_abc', sessionDir });
      const sessionLog = handle.logger.createChild({ agentId: 'agent-0' });
      sessionLog.info('llm request', { turn: 0, step: 1 });
      await handle.flush();
      await getRootLogger().flush();

      const session = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(session).toMatch(/llm request.*agentId=agent-0/);
      expect(session).toMatch(/llm request(?!.*sessionId=ses_abc)/);
      await handle.close();
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });

  it('writes entries without sessionId only to global (not broadcast)', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const handle = getRootLogger().attachSession({ sessionId: 'ses_abc', sessionDir });
      log.info('bootstrap event');
      await getRootLogger().flush();
      await handle.flush();
      const global = await readGlobal();
      expect(global).toContain('bootstrap event');
      let sessionText = '';
      try {
        sessionText = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      } catch {}
      expect(sessionText).not.toContain('bootstrap event');
      await handle.close();
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });

  it('keeps same-id sessions in different directories isolated', async () => {
    const firstDir = await mkdtemp(join(tmpdir(), 'logger-session-a-'));
    const secondDir = await mkdtemp(join(tmpdir(), 'logger-session-b-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const first = getRootLogger().attachSession({ sessionId: 'ses_same', sessionDir: firstDir });
      const second = getRootLogger().attachSession({
        sessionId: 'ses_same',
        sessionDir: secondDir,
      });

      first.logger.info('first only');
      second.logger.info('second only');
      log.info('ambiguous session id', { sessionId: 'ses_same' });
      await getRootLogger().flush();

      const firstText = await readFile(join(firstDir, 'logs', 'kimi-code.log'), 'utf-8');
      const secondText = await readFile(join(secondDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(firstText).toContain('first only');
      expect(firstText).not.toContain('second only');
      expect(firstText).not.toContain('ambiguous session id');
      expect(secondText).toContain('second only');
      expect(secondText).not.toContain('first only');
      expect(secondText).not.toContain('ambiguous session id');

      const global = await readGlobal();
      expect(global).not.toContain('first only');
      expect(global).not.toContain('second only');
      expect(global).toContain('ambiguous session id');

      await first.close();
      await second.close();
    } finally {
      await rm(firstDir, { recursive: true, force: true });
      await rm(secondDir, { recursive: true, force: true });
    }
  });

  it('keeps a reused same-directory session sink open until every handle closes', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-shared-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const first = getRootLogger().attachSession({ sessionId: 'ses_shared', sessionDir });
      const second = getRootLogger().attachSession({ sessionId: 'ses_shared', sessionDir });

      await first.close();
      await first.close();

      second.logger.info('still routes after first close');
      await second.flush();

      const text = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(text).toContain('still routes after first close');
      await second.close();
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });

  it('does not let a closing handle remove a replacement session sink', async () => {
    const firstDir = await mkdtemp(join(tmpdir(), 'logger-session-old-'));
    const secondDir = await mkdtemp(join(tmpdir(), 'logger-session-new-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const first = getRootLogger().attachSession({
        sessionId: 'ses_replace',
        sessionDir: firstDir,
      });

      const closing = first.close();
      const second = getRootLogger().attachSession({
        sessionId: 'ses_replace',
        sessionDir: secondDir,
      });
      await closing;

      second.logger.info('replacement still routes');
      await second.flush();

      const secondText = await readFile(join(secondDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(secondText).toContain('replacement still routes');
      await second.close();
    } finally {
      await rm(firstDir, { recursive: true, force: true });
      await rm(secondDir, { recursive: true, force: true });
    }
  });

  it('waits for a closing session sink when flushing by session id', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-closing-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const handle = getRootLogger().attachSession({ sessionId: 'ses_closing', sessionDir });
      handle.logger.info('close flush marker');

      const closing = handle.close();
      await expect(getRootLogger().flushSession('ses_closing')).resolves.toBe(true);
      await closing;

      const text = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(text).toContain('close flush marker');
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });
});

describe('redact helper', () => {
  it('returns same shape with sensitive fields replaced', () => {
    const out = redact({ user: 'x', token: 'abc', nested: { apiKey: '1' } });
    expect(out.user).toBe('x');
    expect(out.token).toBe('[REDACTED]');
    expect(out.nested.apiKey).toBe('[REDACTED]');
  });

  it('passes primitives through unchanged', () => {
    expect(redact(42)).toBe(42);
    expect(redact('hi')).toBe('hi');
    expect(redact(null)).toBe(null);
  });

  it('processes arrays', () => {
    const out = redact([{ token: '1' }, { apiKey: '2' }]);
    expect(out[0]?.token).toBe('[REDACTED]');
    expect(out[1]?.apiKey).toBe('[REDACTED]');
  });

  it('handles cyclic arrays without recursing forever', () => {
    const input: unknown[] = [];
    input.push(input);

    const out = redact(input);

    expect(out[0]).toBe('[REDACTED:cycle]');
  });
});

  it('session handle.flush waits for in-progress close to finish', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-flush-wait-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const handle = getRootLogger().attachSession({ sessionId: 'ses_wait', sessionDir });
      // Write a line that should end up in the session sink.
      handle.logger.info('flush-wait-marker');
  
      // Start closing but don't await it yet.
      const closing = handle.close();
      // Immediately flush via the handle — this should await the closePromise
      await handle.flush();
      // Now await the close to finish before reading files.
      await closing;
  
      const sessionText = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(sessionText).toContain('flush-wait-marker');
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });


  it('getConfig reflects configuration state before and after configure', async () => {
    // Before configuration getConfig should be undefined
    expect(getRootLogger().getConfig()).toBeUndefined();
    expect(getRootLogger().isConfigured()).toBe(false);
  
    // Configure and verify the stored config is returned
    const cfg = defaultConfig('debug');
    await getRootLogger().configure(cfg);
    const stored = getRootLogger().getConfig();
    expect(stored).toBeDefined();
    // Check a few key fields to ensure it's the same configuration
    expect(stored?.level).toBe('debug');
    expect(stored?.globalLogPath).toBe(cfg.globalLogPath);
    expect(getRootLogger().isConfigured()).toBe(true);
  });


  it('logs function payloads and flushDiagnosticLogs returns true', async () => {
    await getRootLogger().configure(defaultConfig());
    // Named function should render as [Function: foo]
    function foo() {}
    log.warn('function-payload', foo);
    // Flush via the exported convenience wrapper
    await expect(flushDiagnosticLogs()).resolves.toBe(true);
    const text = await readGlobal();
    expect(text).toMatch(/\[Function: foo\]/);
  });


  it('shutdown awaits closing and closes open sessions', async () => {
    const dirA = await mkdtemp(join(tmpdir(), 'logger-shutdown-a-'));
    const dirB = await mkdtemp(join(tmpdir(), 'logger-shutdown-b-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const a = getRootLogger().attachSession({ sessionId: 'sA', sessionDir: dirA });
      const b = getRootLogger().attachSession({ sessionId: 'sB', sessionDir: dirB });
      a.logger.info('marker-A');
      b.logger.info('marker-B');
      // Initiate close on first handle but do not await it so entry becomes 'closing'
      const closing = a.close();
      // Now trigger the test-only shutdown which should handle both the closing entry
      // and the still-open entry (b). This exercises both branches inside __shutdownForTest.
      await __resetRootLoggerForTest();
      // Await the previously started close to ensure no unhandled promise rejections
      await expect(closing).resolves.toBeUndefined();
      // After reset, the global root should be cleared/unconfigured
      expect(getRootLogger().isConfigured()).toBe(false);
      // The session files should still contain the logged markers (sinks were closed)
      const textA = await readFile(join(dirA, 'logs', 'kimi-code.log'), 'utf-8');
      const textB = await readFile(join(dirB, 'logs', 'kimi-code.log'), 'utf-8');
      expect(textA).toContain('marker-A');
      expect(textB).toContain('marker-B');
    } finally {
      await rm(dirA, { recursive: true, force: true });
      await rm(dirB, { recursive: true, force: true });
    }
  });


  it('flushSync writes global and session logs synchronously', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-sync-'));
    try {
      await getRootLogger().configure(defaultConfig());
      const handle = getRootLogger().attachSession({ sessionId: 'sync_sess', sessionDir });
      // Enqueue entries for global and session sinks
      handle.logger.info('sync session line');
      log.info('sync global line');
      // Synchronously flush to disk
      getRootLogger().flushSync();
      // Read files immediately and assert content present
      const globalText = await readGlobal();
      const sessionText = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      expect(globalText).toContain('sync global line');
      expect(sessionText).toContain('sync session line');
      await handle.close();
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });


  it('returns noop handle when not configured or when level off', async () => {
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-noop-'));
    try {
      // Ensure root is not configured (before configure)
      await __resetRootLoggerForTest();
      const root = getRootLogger();
      const handle = root.attachSession({ sessionId: 'noop-sess', sessionDir });
      // noop handle should allow flush/close without throwing
      await expect(handle.flush()).resolves.toBeUndefined();
      await expect(handle.close()).resolves.toBeUndefined();
      // Now configure with level 'off' and verify we get a noop handle again
      await getRootLogger().configure(defaultConfig('off'));
      const handle2 = getRootLogger().attachSession({ sessionId: 'noop-sess-2', sessionDir });
      await expect(handle2.flush()).resolves.toBeUndefined();
      await expect(handle2.close()).resolves.toBeUndefined();
      // There should be no session log file created for noop handles
      let sessionText = '';
      try {
        sessionText = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      } catch {
        sessionText = '';
      }
      expect(sessionText).toBe('');
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });

