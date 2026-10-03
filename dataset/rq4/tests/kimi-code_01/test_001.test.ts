import { it, expect } from 'vitest';
import { McpConnectionManager } from '../../../src/mcp/connection-manager';

it('reconnect sets public entry to pending and clears tools immediately while connectOne is blocked', async () => {
  const cm = new McpConnectionManager();
  // Prepare a controllable connectOne promise.
  let resolveConnect: () => void;
  const connectOnePromise = new Promise<void>((res) => {
    resolveConnect = res;
  });

  // Inject a synthetic internal entry named 'probe' that appears connected
  // and has a non-empty tools list so the clearing is observable.
  const internalEntry = {
    name: 'probe',
    config: { enabled: true, transport: 'stdio' },
    status: 'connected',
    tools: [{ id: 'tool-a' }],
    enabledNames: ['probe'],
    error: undefined,
    client: undefined,
  } as any;

  // Reach into the private entries map (tests in the repo do similar casts).
  (cm as any).entries.set('probe', internalEntry);

  // Override methods deterministically per activation conditions.
  cm.beginConnectAttempt = () => 'attempt-1';
  cm.isCurrent = () => true;
  cm.connectOne = () => connectOnePromise;

  // Start reconnect but do not await it so we can observe the transient public state.
  const reconnectPromise = cm.reconnect('probe');

  // Immediately observe the public view.
  // Independent oracle: status must be 'pending', tools cleared -> toolCount 0, and no error.
  expect(cm.get('probe')).toMatchObject({ status: 'pending', toolCount: 0, error: undefined });

  // Now resolve connectOne and await completion to avoid leaking state.
  resolveConnect!();
  await reconnectPromise;

  // Best-effort cleanup if available.
  if (typeof (cm as any).shutdown === 'function') {
    await (cm as any).shutdown();
  }
});
