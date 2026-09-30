import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("camera_snap_invalid_facing_round_010", async () => {
    // readStringParam and gateway helpers must exist; resolveNode is used before facing validation so mock nodes-utils
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/common.js", () => ({
      readStringParam: (params, name, opts) => {
        const v = params && Object.prototype.hasOwnProperty.call(params, name) ? params[name] : undefined;
        if (opts && opts.required && (v === undefined || v === null || String(v) === "")) {
          throw new Error(`missing param ${name}`);
        }
        return v;
      },
    }));

    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/gateway.js", () => ({
      readGatewayCallOptions: (params) => ({}),
      callGatewayTool: async () => ({}),
    }));

    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/nodes-utils.js", () => ({
      resolveNode: async (gatewayOpts, node) => ({ nodeId: `node:${String(node)}`, remoteIp: "127.0.0.1" }),
    }));

    const mod = await __testAugmentLoadTarget_2a3213d800a4();
    const { createNodesTool } = mod;
    const tool = createNodesTool();

    // Act & Assert: invalid facing should be rejected with the specific facing validation error
    await __testAugmentVitest_2216b4bb520e.expect(
      tool.execute("call-camera-1", { action: "camera_snap", node: "n1", facing: "sideways" }),
    ).rejects.toThrow("invalid facing (front|back|both)");
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
