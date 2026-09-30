import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("invoke_params_json_invalid_round_010_pass_02", async () => {
    // resolveNodeId must exist because invoke path calls it before JSON parse
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/nodes-utils.js", () => ({
      resolveNodeId: async () => "node:1",
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
      jsonResult: (payload) => ({ ok: true, payload }),
    }));

    // Gateway is not expected to be reached before parse error, but provide a no-op implementation.
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool: async () => ({}),
      readGatewayCallOptions: () => ({}),
    }));

    const mod = await __testAugmentLoadTarget_2a3213d800a4();
    const { createNodesTool } = mod;
    const tool = createNodesTool();

    // invokeParamsJson is invalid JSON and should trigger the JSON parsing error branch
    await __testAugmentVitest_2216b4bb520e.expect(
      tool.execute("t4", { action: "invoke", node: "n1", invokeCommand: "custom.cmd", invokeParamsJson: "{not:json}" }),
    ).rejects.toThrow(/invokeParamsJson must be valid JSON/i);
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
