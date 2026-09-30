import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("notify_requires_title_or_body_round_010", async () => {
    // Arrange: only the minimal helpers are mocked. notify validation happens before any gateway calls.
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/common.js", () => ({
      readStringParam: (params, name, opts) => {
        const v = (params && Object.prototype.hasOwnProperty.call(params, name)) ? params[name] : undefined;
        if (opts && opts.required && (v === undefined || v === null || String(v) === "")) {
          throw new Error(`missing param ${name}`);
        }
        return v;
      },
      readGatewayCallOptions: (params) => ({}),
      jsonResult: (payload) => ({ ok: true, payload }),
    }));

    // We do not need to mock nodes-utils because notify validation fails before resolving node id.

    const { createNodesTool } = await __testAugmentLoadTarget_2a3213d800a4();
    const tool = createNodesTool();

    // Act & Assert: missing title & body should cause an error containing 'title or body required'
    await __testAugmentVitest_2216b4bb520e.expect(
      tool.execute("call-2", { action: "notify", node: "n1" }),
    ).rejects.toThrow("title or body required");
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
