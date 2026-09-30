import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("device_info_invoke_payload_round_010_pass_02", async () => {
    // Mock gateway to return a payload for node.invoke
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool: async (action) => {
        if (action === "node.invoke") return { payload: { info: "ok" } };
        return {};
      },
      readGatewayCallOptions: () => ({}),
    }));

    // Minimal common helpers
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/common.js", () => ({
      readStringParam: (params, name, opts) => {
        const v = params && Object.prototype.hasOwnProperty.call(params, name) ? params[name] : undefined;
        if (opts && opts.required && (v === undefined || v === null || String(v) === "")) {
          throw new Error(`missing param ${name}`);
        }
        return v;
      },
      jsonResult: (payload) => ({ ok: true, payload }),
    }));

    // resolveNodeId used by invokeNodeCommandPayload
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/nodes-utils.js", () => ({
      resolveNodeId: async (_gatewayOpts, node) => `node:${String(node)}`,
    }));

    const mod = await __testAugmentLoadTarget_2a3213d800a4();
    const { createNodesTool } = mod;
    const tool = createNodesTool();

    const res = await tool.execute("t1", { action: "device_info", node: "n1" });

    __testAugmentVitest_2216b4bb520e.expect(res).toBeTruthy();
    __testAugmentVitest_2216b4bb520e.expect(res.ok).toBe(true);
    __testAugmentVitest_2216b4bb520e.expect(res.payload).toEqual({ info: "ok" });
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
