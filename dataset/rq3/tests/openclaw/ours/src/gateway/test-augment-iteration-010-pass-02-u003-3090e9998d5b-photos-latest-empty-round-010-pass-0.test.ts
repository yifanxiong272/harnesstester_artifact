import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("photos_latest_empty_round_010_pass_02", async () => {
    // Gateway returns a payload without photos (empty path)
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool: async (action) => {
        if (action === "node.invoke") return { payload: {} };
        return {};
      },
      readGatewayCallOptions: () => ({}),
    }));

    // resolveNode used by photos_latest
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/nodes-utils.js", () => ({
      resolveNode: async () => ({ nodeId: "node:1", remoteIp: "127.0.0.1" }),
    }));

    // sanitize should be exercised; return identity
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tool-images.js", () => ({
      sanitizeToolResultImages: async (result) => result,
    }));

    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/common.js", () => ({
      readStringParam: (params, name, opts) => {
        const v = params && Object.prototype.hasOwnProperty.call(params, name) ? params[name] : undefined;
        if (opts && opts.required && (v === undefined || v === null || String(v) === "")) {
          throw new Error(`missing param ${name}`);
        }
        return v;
      },
      readGatewayCallOptions: () => ({}),
    }));

    const mod = await __testAugmentLoadTarget_2a3213d800a4();
    const { createNodesTool } = mod;
    const tool = createNodesTool({ modelHasVision: true });

    const res = await tool.execute("t3", { action: "photos_latest", node: "n1" });

    // photos_latest empty result should have empty content and details arrays
    __testAugmentVitest_2216b4bb520e.expect(res).toBeTruthy();
    __testAugmentVitest_2216b4bb520e.expect(Array.isArray(res.content)).toBe(true);
    __testAugmentVitest_2216b4bb520e.expect(res.content.length).toBe(0);
    __testAugmentVitest_2216b4bb520e.expect(Array.isArray(res.details)).toBe(true);
    __testAugmentVitest_2216b4bb520e.expect(res.details.length).toBe(0);
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
