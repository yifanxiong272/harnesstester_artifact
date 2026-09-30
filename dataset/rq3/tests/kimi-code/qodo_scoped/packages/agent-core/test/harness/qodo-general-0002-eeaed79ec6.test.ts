import { mkdtemp, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createRPC,
  KimiCore,
  type CoreAPI,
  type SDKAPI,
  type TelemetryClient,
} from '../../src';
import {
  __resetRootLoggerForTest,
  getRootLogger,
} from '../../src/logging/logger';
import { resolveLoggingConfig } from '../../src/logging/resolve-config';
import {
  recordingContextTelemetry,
  type TelemetryContextRecord,
} from '../fixtures/telemetry';

const CONFIG = `
default_model = "kimi-code/kimi-for-coding"

[providers."managed:kimi-code"]
type = "kimi"
api_key = "test-key"
base_url = "https://api.example/v1"

[models."kimi-code/kimi-for-coding"]
provider = "managed:kimi-code"
model = "kimi-for-coding"
max_context_size = 1000000
`;

describe('HarnessAPI session model aliases', () => {
  let tmp: string;
  let homeDir: string;
  let workDir: string;
  let configPath: string;

  beforeEach(async () => {
    tmp = await mkdtemp(join(tmpdir(), 'kimi-model-alias-'));
    homeDir = join(tmp, 'home');
    workDir = join(tmp, 'work');
    configPath = join(tmp, 'config.toml');
    await mkdir(workDir, { recursive: true });
    await writeFile(configPath, CONFIG);
  });

  afterEach(async () => {
    await __resetRootLoggerForTest();
    await rm(tmp, { recursive: true, force: true });
  });

  it('keeps the configured alias separate from the provider model across create, setModel, and resume', async () => {
    const rpc = await createTestRpc();
    const created = await rpc.createSession({
      workDir,
      model: 'kimi-code/kimi-for-coding',
    });

    expect(await rpc.getModel({ sessionId: created.id, agentId: 'main' })).toBe(
      'kimi-code/kimi-for-coding',
    );

    const config = await rpc.getConfig({ sessionId: created.id, agentId: 'main' });
    expect(config.modelAlias).toBe('kimi-code/kimi-for-coding');
    expect(config.provider?.model).toBe('kimi-for-coding');
    expect(config.modelCapabilities?.max_context_tokens).toBe(1_000_000);

    await rpc.setModel({
      sessionId: created.id,
      agentId: 'main',
      model: 'kimi-code/kimi-for-coding',
    });

    const freshRpc = await createTestRpc();
    await freshRpc.resumeSession({ sessionId: created.id });

    expect(await freshRpc.getModel({ sessionId: created.id, agentId: 'main' })).toBe(
      'kimi-code/kimi-for-coding',
    );
  });

  it('re-bootstraps profile and model when resuming a session whose wire has no config.update', async () => {
    // A migrated session ships a wire.jsonl with only `metadata` and message
    // records — none of the `config.update` / `tools.set_active_tools`
    // bootstrap events a natively-created session writes. Resuming it must
    // still yield a usable agent (model + system prompt), not an empty config.
    const rpc = await createTestRpc();
    const created = await rpc.createSession({
      workDir,
      model: 'kimi-code/kimi-for-coding',
    });
    await rpc.closeSession({ sessionId: created.id });

    const wirePath = await findWireFile(homeDir);
    const kept = (await readFile(wirePath, 'utf-8'))
      .split('\n')
      .filter((line) => line.trim().length > 0)
      .filter((line) => {
        const type = (JSON.parse(line) as { type?: string }).type;
        return type !== 'config.update' && type !== 'tools.set_active_tools';
      });
    await writeFile(wirePath, `${kept.join('\n')}\n`);

    const freshRpc = await createTestRpc();
    await freshRpc.resumeSession({ sessionId: created.id });

    expect(await freshRpc.getModel({ sessionId: created.id, agentId: 'main' })).toBe(
      'kimi-code/kimi-for-coding',
    );
    const config = await freshRpc.getConfig({ sessionId: created.id, agentId: 'main' });
    expect(config.modelAlias).toBe('kimi-code/kimi-for-coding');
    expect(config.systemPrompt.length).toBeGreaterThan(0);
  });

  it('applies RPC config updates to later agent model changes', async () => {
    const rpc = await createTestRpc();
    const created = await rpc.createSession({
      workDir,
      model: 'kimi-code/kimi-for-coding',
    });

    const updatedConfig = await rpc.setKimiConfig({
      defaultModel: 'gpt-alias',
      providers: {
        openai: {
          type: 'openai',
          apiKey: 'sk-openai',
          baseUrl: 'https://openai.example/v1',
        },
      },
      models: {
        'gpt-alias': {
          provider: 'openai',
          model: 'gpt-runtime',
          maxContextSize: 200000,
          capabilities: ['tool_use'],
        },
      },
    });
    expect(updatedConfig.defaultModel).toBe('gpt-alias');

    await expect(
      rpc.setModel({
        sessionId: created.id,
        agentId: 'main',
        model: 'gpt-alias',
      }),
    ).resolves.toEqual({
      model: 'gpt-alias',
      providerName: 'openai',
    });

    const config = await rpc.getConfig({ sessionId: created.id, agentId: 'main' });
    expect(config.modelAlias).toBe('gpt-alias');
    expect(config.provider).toMatchObject({
      type: 'openai',
      model: 'gpt-runtime',
      apiKey: 'sk-openai',
      baseUrl: 'https://openai.example/v1',
    });
    expect(config.modelCapabilities).toMatchObject({
      tool_use: true,
      max_context_tokens: 200000,
    });
  });

  it('can create an unconfigured session when no model is selected', async () => {
    await writeFile(configPath, '');
    const rpc = await createTestRpc();

    const created = await rpc.createSession({ workDir });

    expect(created.id.startsWith('session_')).toBe(true);
    expect(await rpc.getModel({ sessionId: created.id, agentId: 'main' })).toBe('');
  });

  it('loads configured permission rules into created and resumed sessions', async () => {
    await writeFile(
      configPath,
      `${CONFIG}

[[permission.deny]]
tool = "Bash"
match = "rm *"
reason = "no rm"
`,
    );
    const rpc = await createTestRpc();
    const created = await rpc.createSession({ workDir });

    await expect(rpc.getPermission({ sessionId: created.id, agentId: 'main' })).resolves.toEqual({
      mode: 'manual',
      rules: [
        {
          decision: 'deny',
          scope: 'user',
          pattern: 'Bash(rm *)',
          reason: 'no rm',
        },
      ],
    });

    const freshRpc = await createTestRpc();
    await freshRpc.resumeSession({ sessionId: created.id });
    await expect(
      freshRpc.getPermission({ sessionId: created.id, agentId: 'main' }),
    ).resolves.toEqual({
      mode: 'manual',
      rules: [
        {
          decision: 'deny',
          scope: 'user',
          pattern: 'Bash(rm *)',
          reason: 'no rm',
        },
      ],
    });
  });

  it('uses configured default permission mode for fresh sessions', async () => {
    await writeFile(
      configPath,
      CONFIG.replace(
        'default_model = "kimi-code/kimi-for-coding"',
        'default_model = "kimi-code/kimi-for-coding"\ndefault_permission_mode = "auto"',
      ),
    );
    const rpc = await createTestRpc();
    const created = await rpc.createSession({ workDir });

    await expect(rpc.getPermission({ sessionId: created.id, agentId: 'main' })).resolves.toEqual({
      mode: 'auto',
      rules: [],
    });

    const explicit = await rpc.createSession({ workDir, permission: 'manual' });
    await expect(rpc.getPermission({ sessionId: explicit.id, agentId: 'main' })).resolves.toEqual({
      mode: 'manual',
      rules: [],
    });
  });

  it('does not expose raw provider switching through the core RPC surface', async () => {
    const rpc = (await createTestRpc()) as unknown as Record<string, unknown>;

    expect(rpc['setProvider']).toBeUndefined();
  });

  it('exposes the core package version as read-only metadata', async () => {
    const rpc = await createTestRpc();
    const pkg = JSON.parse(
      await readFile(new URL('../../package.json', import.meta.url), 'utf-8'),
    ) as { version: string };

    await expect(rpc.getCoreInfo({})).resolves.toEqual({
      version: pkg.version,
    });
    expect((rpc as unknown as Record<string, unknown>)['setVersion']).toBeUndefined();
  });

  it('keeps the resumed model alias visible when it no longer resolves', async () => {
    const rpc = await createTestRpc();
    const created = await rpc.createSession({ workDir, model: 'kimi-code/kimi-for-coding' });
    await rpc.closeSession({ sessionId: created.id });

    // The config now has no models and no default model — the alias replayed
    // from the session is invalid and there is no fallback to resolve.
    await writeFile(configPath, '');

    const freshRpc = await createTestRpc();
    await freshRpc.resumeSession({ sessionId: created.id });

    // The stale alias stays visible so the UI can surface which model the
    // user had selected. The next prompt will raise MODEL_NOT_CONFIGURED.
    expect(await freshRpc.getModel({ sessionId: created.id, agentId: 'main' })).toBe(
      'kimi-code/kimi-for-coding',
    );
  });

  it('logs app_version when resuming a session', async () => {
    await getRootLogger().configure(resolveLoggingConfig({ homeDir }));
    const rpc = await createTestRpc();
    const created = await rpc.createSession({ workDir, model: 'kimi-code/kimi-for-coding' });
    await rpc.closeSession({ sessionId: created.id });

    const freshRpc = await createTestRpc({ appVersion: '1.2.3-test' });
    await freshRpc.resumeSession({ sessionId: created.id });
    await getRootLogger().flushSession(created.id);

    const logText = await readFile(join(created.sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
    expect(logText).toContain('session resume');
    expect(logText).toContain('app_version=1.2.3-test');
  });

  it('surfaces a config error when a resumed model is configured but unresolvable', async () => {
    const rpc = await createTestRpc();
    const created = await rpc.createSession({ workDir, model: 'kimi-code/kimi-for-coding' });
    await rpc.closeSession({ sessionId: created.id });

    // The model alias is still in config, but it now references a provider
    // that does not exist. That is an actionable config error — resume must
    // surface it, not silently fall back to another model or clear it.
    await writeFile(
      configPath,
      `
default_model = "kimi-code/kimi-for-coding"

[providers."managed:kimi-code"]
type = "kimi"
api_key = "test-key"
base_url = "https://api.example/v1"

[models."kimi-code/kimi-for-coding"]
provider = "ghost-provider"
model = "kimi-for-coding"
max_context_size = 1000000
`,
    );

    const freshRpc = await createTestRpc();
    await expect(freshRpc.resumeSession({ sessionId: created.id })).rejects.toThrow();
  });

  it('scopes agent telemetry events to the owning session', async () => {
    const createRecords: TelemetryContextRecord[] = [];
    const createRpc = await createTestRpc({ telemetry: recordingContextTelemetry(createRecords) });
    const created = await createRpc.createSession({
      workDir,
      model: 'kimi-code/kimi-for-coding',
    });

    await createRpc.setPermission({ sessionId: created.id, agentId: 'main', mode: 'yolo' });

    expect(createRecords).toContainEqual({
      event: 'yolo_toggle',
      sessionId: created.id,
      properties: { enabled: true },
    });

    await createRpc.setPermission({ sessionId: created.id, agentId: 'main', mode: 'auto' });

    expect(createRecords).toContainEqual({
      event: 'afk_toggle',
      sessionId: created.id,
      properties: { enabled: true },
    });

    await createRpc.setKimiConfig({
      defaultModel: 'gpt-alias',
      providers: {
        openai: {
          type: 'openai',
          apiKey: 'sk-openai',
          baseUrl: 'https://openai.example/v1',
        },
      },
      models: {
        'gpt-alias': {
          provider: 'openai',
          model: 'gpt-runtime',
          maxContextSize: 200000,
        },
      },
    });
    await createRpc.setModel({
      sessionId: created.id,
      agentId: 'main',
      model: 'gpt-alias',
    });

    expect(createRecords).toContainEqual({
      event: 'model_switch',
      sessionId: created.id,
      properties: { model: 'gpt-alias' },
    });

    const resumeRecords: TelemetryContextRecord[] = [];
    const resumeRpc = await createTestRpc({ telemetry: recordingContextTelemetry(resumeRecords) });
    await resumeRpc.resumeSession({ sessionId: created.id });
    await resumeRpc.setThinking({ sessionId: created.id, agentId: 'main', level: 'off' });

    expect(resumeRecords).toContainEqual({
      event: 'thinking_toggle',
      sessionId: created.id,
      properties: { enabled: false },
    });
  });

  it('tracks session_load_failed with the attempted session context', async () => {
    const rpc = await createTestRpc();
    const created = await rpc.createSession({ workDir });
    await writeFile(join(created.sessionDir, 'state.json'), '{bad json', 'utf-8');

    const records: TelemetryContextRecord[] = [];
    const freshRpc = await createTestRpc({ telemetry: recordingContextTelemetry(records) });

    await expect(freshRpc.resumeSession({ sessionId: created.id })).rejects.toThrow();
    expect(records).toContainEqual({
      event: 'session_load_failed',
      sessionId: created.id,
      properties: { reason: 'SyntaxError' },
    });
  });

  it('adds web client metadata to new-session telemetry', async () => {
    const records: TelemetryContextRecord[] = [];
    const rpc = await createTestRpc({ telemetry: recordingContextTelemetry(records) });
    const created = await rpc.createSession({
      workDir,
      client: {
        id: 'web_test_client',
        name: 'kimi-code-web',
        version: '0.1.1',
        uiMode: 'web',
      },
    });

    expect(records).toContainEqual({
      event: 'session_started',
      sessionId: created.id,
      properties: {
        client_id: 'web_test_client',
        client_name: 'kimi-code-web',
        client_version: '0.1.1',
        ui_mode: 'web',
        resumed: false,
      },
    });

    await rpc.setPermission({ sessionId: created.id, agentId: 'main', mode: 'yolo' });

    expect(records).toContainEqual({
      event: 'yolo_toggle',
      sessionId: created.id,
      properties: {
        client_id: 'web_test_client',
        client_name: 'kimi-code-web',
        client_version: '0.1.1',
        ui_mode: 'web',
        enabled: true,
      },
    });
  });

  async function findWireFile(root: string): Promise<string> {
    const suffix = join('agents', 'main', 'wire.jsonl');
    const entries = await readdir(root, { recursive: true });
    const match = entries.find((entry) => entry.endsWith(suffix));
    if (match === undefined) {
      throw new Error('wire.jsonl not found under session home');
    }
    return join(root, match);
  }

  async function createTestRpc(
    options: {
      readonly appVersion?: string;
      readonly telemetry?: TelemetryClient;
    } = {},
  ) {
    const [coreRpc, sdkRpc] = createRPC<CoreAPI, SDKAPI>();
    void new KimiCore(coreRpc, {
      homeDir,
      configPath,
      appVersion: options.appVersion,
      telemetry: options.telemetry,
    });
    return sdkRpc({
      emitEvent: vi.fn(),
      requestApproval: vi.fn(async () => ({ decision: 'rejected' as const })),
      requestQuestion: vi.fn(async () => null),
      toolCall: vi.fn(async () => ({ output: '' })),
    });
  }

  it('throws when getting info for a non-installed plugin', async () => {
    const [coreRpc] = createRPC<CoreAPI, SDKAPI>();
    const core = new KimiCore(coreRpc, { homeDir, configPath });
    await (core as any).pluginsReady;
    // Ensure no load error is present so the not-found branch is reached.
    (core as any).pluginsLoadError = undefined;
    await expect(core.getPluginInfo({ id: 'no-such-plugin' })).rejects.toThrow(
      /Plugin "no-such-plugin" is not installed/,
    );
  });


  it('throws when plugin state failed to load is set', async () => {
    const [coreRpc] = createRPC<CoreAPI, SDKAPI>();
    const core = new KimiCore(coreRpc, { homeDir, configPath });
    // Ensure any background plugin load has settled.
    await (core as any).pluginsReady;
    // Simulate a captured plugin-load error (as the constructor would set).
    (core as any).pluginsLoadError = new Error('simulated plugin load failure');
    await expect(core.listPlugins({})).rejects.toThrow(/Plugin state failed to load/);
  });


  it('surfaces plugin reload errors and sets pluginsLoadError', async () => {
    const [coreRpc] = createRPC<CoreAPI, SDKAPI>();
    const core = new KimiCore(coreRpc, { homeDir, configPath });
    // Prevent the real PluginManager load from interfering with our stub.
    (core as any).pluginsReady = Promise.resolve();
    // Replace plugins with a stub that throws on reload.
    (core as any).plugins = {
      reload: async () => {
        throw new Error('plugin-reload-boom');
      },
    };
  
    await expect(core.reloadPlugins({})).rejects.toThrow(/Failed to reload plugins|plugin-reload-boom/);
    // The underlying error should be stored on the core instance.
    expect((core as any).pluginsLoadError).toBeInstanceOf(Error);
    expect((core as any).pluginsLoadError.message).toBe('plugin-reload-boom');
  });


  it('merges managed KIMI env into stdio plugin servers only', async () => {
    const [coreRpc] = createRPC<CoreAPI, SDKAPI>();
    const core = new KimiCore(coreRpc, { homeDir, configPath });
    await (core as any).pluginsReady;
  
    // Provide a provider so managed env returns something.
    (core as any).config.providers = {
      'managed:kimi-code': { baseUrl: 'https://provider.example' },
    };
  
    // Simulate plugin servers: one stdio and one tcp.
    const pluginServers = {
      stdioSrv: { transport: 'stdio', env: { EXIST: '1' } },
      tcpSrv: { transport: 'tcp', env: { KEEP: 'y' } },
    };
  
    // Set an environment override to ensure it's merged in.
    process.env.KIMI_CODE_BASE_URL = 'https://env.example/';
  
    const merged = (core as any).withManagedKimiPluginEnv(pluginServers);
  
    // stdio server should have the managed env merged and keep its original env.
    expect(merged.stdioSrv.env.EXIST).toBe('1');
    expect(merged.stdioSrv.env.KIMI_CODE_BASE_URL).toBe('https://env.example');
  
    // tcp server should be unchanged (no added managed env).
    expect(merged.tcpSrv).toEqual(pluginServers.tcpSrv);
  
    // Cleanup
    delete process.env.KIMI_CODE_BASE_URL;
  });


  it('removeKimiProvider removes provider, models, and defaultModel', async () => {
    const rpc = await createTestRpc();
    const updated = await rpc.removeKimiProvider({ providerId: 'managed:kimi-code' });
    // provider should be removed
    expect(updated.providers && (updated.providers as Record<string, unknown>)['managed:kimi-code']).toBeUndefined();
    // defaultModel referenced the removed model in the fixture; it should be cleared
    expect(updated.defaultModel).toBeUndefined();
    // models referencing the provider should be removed (either undefined or empty)
    const models = updated.models as Record<string, unknown> | undefined;
    expect(models === undefined || Object.keys(models).length === 0).toBe(true);
  });


  it('throws when creating a session without workDir', async () => {
    const rpc = await createTestRpc();
    // createSession requires a non-empty workDir and should reject with a message
    await expect(rpc.createSession({} as any)).rejects.toThrow('requires workDir');
  });

});
