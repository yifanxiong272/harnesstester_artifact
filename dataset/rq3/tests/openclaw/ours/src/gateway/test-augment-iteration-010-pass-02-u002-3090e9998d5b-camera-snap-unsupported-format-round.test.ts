import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {

  __testAugmentVitest_2216b4bb520e.it("camera_snap_unsupported_format_round_010_pass_02", async () => {
    // Gateway returns a raw payload placeholder; parseCameraSnapPayload will normalize it to GIF
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool: async () => ({ payload: {} }),
      readGatewayCallOptions: () => ({}),
    }));

    // Mock CLI camera parser to return an unsupported format (GIF)
    __testAugmentVitest_2216b4bb520e.vi.doMock("../cli/nodes-camera.js", () => ({
      parseCameraSnapPayload: (_raw) => ({ format: "GIF", base64: undefined, width: 1, height: 1 }),
      cameraTempPath: (_opts) => "/tmp/fake.snap",
      writeCameraPayloadToFile: async () => {},
    }));

    // resolveNode used by camera_snap
    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/nodes-utils.js", () => ({
      resolveNode: async (_gatewayOpts, node) => ({ nodeId: `node:${String(node)}`, remoteIp: "127.0.0.1" }),
    }));

    __testAugmentVitest_2216b4bb520e.vi.doMock("../agents/tools/common.js", () => ({
      readStringParam: (params, name, opts) => {
        const v = params && Object.prototype.hasOwnProperty.call(params, name) ? params[name] : undefined;
        if (opts && opts.required && (v === undefined || v === null || String(v) === "")) {
          throw new Error(`missing param ${name}`);
        }
        return v;
      },
    }));

    const mod = await __testAugmentLoadTarget_2a3213d800a4();
    const { createNodesTool } = mod;
    const tool = createNodesTool();

    await __testAugmentVitest_2216b4bb520e.expect(
      tool.execute("t2", { action: "camera_snap", node: "n1", facing: "front" }),
    ).rejects.toThrow(/unsupported camera.snap format/i);
  });
});

import * as __testAugmentVitest_2216b4bb520e from "vitest";

const __testAugmentLoadTarget_2a3213d800a4 = async () => {
  __testAugmentVitest_2216b4bb520e.vi.doUnmock("../agents/tools/nodes-tool.js");
  __testAugmentVitest_2216b4bb520e.vi.resetModules();
  return import("../agents/tools/nodes-tool.js");
};
