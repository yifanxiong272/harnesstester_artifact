import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("approve_node_pair_scopes_round_010", async () => {
    // Mock gateway exports (callGatewayTool + readGatewayCallOptions) to provide a pending list and approve response
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool: async (action, gatewayOpts, payload, opts) => {
        if (action === "node.pair.list") {
          return { pending: [{ requestId: "r1", commands: ["some:command"] }] };
        }
        if (action === "node.pair.approve") {
          return { approved: true };
        }
        return {};
      },
      readGatewayCallOptions: (params) => ({}),
    }));

    // Mock common utilities used by the tool
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

    // Load the target after mocks are registered
    const mod = await __testAugmentLoadTarget_2a3213d800a4();
    const { createNodesTool } = mod;
    const tool = createNodesTool();

    // Act
    const res = await tool.execute("call-approve-1", { action: "approve", requestId: "r1" });

    // Assert
    __testAugmentVitest_2216b4bb520e.expect(res).toBeTruthy();
    __testAugmentVitest_2216b4bb520e.expect(res.ok).toBe(true);
    __testAugmentVitest_2216b4bb520e.expect(res.payload).toEqual({ approved: true });
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
