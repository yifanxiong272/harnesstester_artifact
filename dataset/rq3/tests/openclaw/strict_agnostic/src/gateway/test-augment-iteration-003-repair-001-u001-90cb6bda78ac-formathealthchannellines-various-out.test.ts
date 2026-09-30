import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, test, vi } from "vitest";
import { WebSocket } from "ws";
import { CONFIG_PATH } from "../config/config.js";
import type { DeviceIdentity } from "../infra/device-identity.js";
import { resolveRestartSentinelPath } from "../infra/restart-sentinel.js";
import { GATEWAY_CLIENT_MODES, GATEWAY_CLIENT_NAMES } from "../utils/message-channel.js";
import type { GatewayClient } from "./client.js";

vi.mock("../infra/update-runner.js", () => ({
  runGatewayUpdate: vi.fn(async () => ({
    status: "ok",
    mode: "git",
    root: "/repo",
    steps: [],
    durationMs: 12,
  })),
}));

import { runGatewayUpdate } from "../infra/update-runner.js";
import { connectGatewayClient } from "./test-helpers.e2e.js";
import { installGatewayTestHooks, onceMessage, rpcReq } from "./test-helpers.js";
import { installConnectedControlUiServerSuite } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });
const FAST_WAIT_OPTS = { timeout: 1_000, interval: 2 } as const;

let ws: WebSocket;
let port: number;

installConnectedControlUiServerSuite((started) => {
  ws = started.ws;
  port = started.port;
});

const connectNodeClient = async (params: {
  port: number;
  commands: string[];
  platform?: string;
  deviceFamily?: string;
  deviceIdentity?: DeviceIdentity;
  instanceId?: string;
  displayName?: string;
  onEvent?: (evt: { event?: string; payload?: unknown }) => void;
}) => {
  const token = process.env.OPENCLAW_GATEWAY_TOKEN;
  if (!token) {
    throw new Error("OPENCLAW_GATEWAY_TOKEN is required for node test clients");
  }
  return await connectGatewayClient({
    url: `ws://127.0.0.1:${params.port}`,
    token,
    role: "node",
    clientName: GATEWAY_CLIENT_NAMES.NODE_HOST,
    clientVersion: "1.0.0",
    clientDisplayName: params.displayName,
    platform: params.platform ?? "ios",
    deviceFamily: params.deviceFamily,
    mode: GATEWAY_CLIENT_MODES.NODE,
    instanceId: params.instanceId,
    scopes: [],
    commands: params.commands,
    deviceIdentity: params.deviceIdentity,
    onEvent: params.onEvent,
    timeoutMessage: "timeout waiting for node to connect",
  });
};

const approveAllPendingPairings = async () => {
  const { approveDevicePairing, listDevicePairing } = await import("../infra/device-pairing.js");
  const list = await listDevicePairing();
  for (const pending of list.pending) {
    await approveDevicePairing(pending.requestId, {
      callerScopes: pending.scopes ?? ["operator.admin"],
    });
  }
};

const connectNodeClientWithPairing = async (params: Parameters<typeof connectNodeClient>[0]) => {
  try {
    return await connectNodeClient(params);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes("pairing required")) {
      throw error;
    }
    await approveAllPendingPairings();
    return await connectNodeClient(params);
  }
};



describe("gateway node command allowlist", () => {


  __testAugmentVitest_bdbc8ca685bd.test("formatHealthChannelLines_various_outcomes_round_003", async () => {
    // Ensure we get the real module implementation even if a hoisted mock exists.
    __testAugmentVitest_bdbc8ca685bd.vi.doMock("../commands/health.js", async () => {
      return await __testAugmentVitest_bdbc8ca685bd.vi.importActual("../commands/health.js");
    });

    const mod = await __testAugmentLoadTarget_788c00a685cb();
    const { formatHealthChannelLines } = mod;

    // 1) linked with auth age -> should show linked and rounded minutes
    const summaryLinked = {
      channels: { ch1: { linked: true, authAgeMs: 120_000 } },
      channelOrder: ["ch1"],
      channelLabels: { ch1: "MyChannel" },
    };
    __testAugmentVitest_bdbc8ca685bd.expect(formatHealthChannelLines(summaryLinked)).toEqual([
      "MyChannel: linked (auth age 2m)",
    ]);

    // 2) not configured -> should emit 'not configured'
    const summaryNotConfigured = {
      channels: { chX: { configured: false } },
      channelOrder: ["chX"],
      channelLabels: { chX: "ChannelX" },
    };
    __testAugmentVitest_bdbc8ca685bd.expect(formatHealthChannelLines(summaryNotConfigured)).toEqual([
      "ChannelX: not configured",
    ]);

    // 3) probe failure with status and error -> formats as failed (status) - error
    const summaryProbeFail = {
      channels: { chFail: { probe: { ok: false, status: 500, error: "boom" } } },
      channelOrder: ["chFail"],
      channelLabels: { chFail: "FailChannel" },
    };
    __testAugmentVitest_bdbc8ca685bd.expect(formatHealthChannelLines(summaryProbeFail)).toEqual([
      "FailChannel: failed (500) - boom",
    ]);

    // 4) account-mode 'all' with an account that has elapsedMs and bot username -> per-account timing listed
    const summaryAccountTiming = {
      channels: {
        chA: {
          accounts: {
            acct1: {
              accountId: "acct1",
              probe: { ok: true, elapsedMs: 123, bot: { username: "bot1" } },
            },
          },
        },
      },
      channelOrder: ["chA"],
      channelLabels: { chA: "AcctChannel" },
    };
    __testAugmentVitest_bdbc8ca685bd.expect(
      formatHealthChannelLines(summaryAccountTiming, { accountMode: "all" }),
    ).toEqual(["AcctChannel: ok (@bot1:acct1:123ms)"]);
  });
});

import * as __testAugmentVitest_bdbc8ca685bd from "vitest";

const __testAugmentLoadTarget_788c00a685cb = async () => {
  __testAugmentVitest_bdbc8ca685bd.vi.doUnmock("../commands/health.js");
  __testAugmentVitest_bdbc8ca685bd.vi.resetModules();
  return import("../commands/health.js");
};
