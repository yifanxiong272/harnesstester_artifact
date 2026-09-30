import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("invoke_pairing_required_message_round_010", async () => {
    // Mock gateway so node.invoke throws a 'not paired' error that includes a requestId in parentheses
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool: async (action, gatewayOpts, payload, opts) => {
        if (action === "node.invoke") {
          throw new Error("Not_Paired (requestId: ABC123)");
        }
        return {};
      },
      readGatewayCallOptions: (params) => ({}),
    }));

    // common read helper
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/common.js", () => ({
      readStringParam: (params, name, opts) => {
        const v = params && Object.prototype.hasOwnProperty.call(params, name) ? params[name] : undefined;
        if (opts && opts.required && (v === undefined || v === null || String(v) === "")) {
          throw new Error(`missing param ${name}`);
        }
        return v;
      },
    }));

    // resolveNodeId is used before invoking; provide a trivial implementation
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/nodes-utils.js", () => ({
      resolveNodeId: async (gatewayOpts, node) => `node:${String(node)}`,
    }));

    const mod = await __testAugmentLoadTarget_2a3213d800a4();
    const { createNodesTool } = mod;
    const tool = createNodesTool();

    // Act & Assert: the thrown 'Not_Paired (requestId: ABC123)' should be recognized and translated
    await __testAugmentVitest_2216b4bb520e.expect(
      tool.execute("call-invoke-1", { action: "invoke", node: "n1", invokeCommand: "cmd" }),
    ).rejects.toThrow(/pairing required before node invoke/i);

    // Also assert the extracted request id appears in the final message
    try {
      await tool.execute("call-invoke-2", { action: "invoke", node: "n1", invokeCommand: "cmd" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      __testAugmentVitest_2216b4bb520e.expect(msg).toContain("ABC123");
    }
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
