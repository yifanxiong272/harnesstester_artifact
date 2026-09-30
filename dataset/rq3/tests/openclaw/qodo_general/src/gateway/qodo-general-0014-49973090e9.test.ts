import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";
import { vi } from "vitest";
import { createNodesTool } from "../agents/tools/nodes-tool.js";

installGatewayTestHooks({ scope: "suite" });

describe("gateway tools.effective", () => {
  it("returns effective tool inventory data", async () => {
    await withServer(async (ws) => {
      await connectOk(ws, { token: "secret", scopes: ["operator.read", "operator.write"] });
      const created = await rpcReq<{ key?: string }>(ws, "sessions.create", {
        label: "Tools Effective Test",
      });
      expect(created.ok).toBe(true);
      const sessionKey = created.payload?.key;
      expect(sessionKey).toBeTruthy();
      const res = await rpcReq<{
        agentId?: string;
        groups?: Array<{
          id?: "core" | "plugin" | "channel";
          source?: "core" | "plugin" | "channel";
          tools?: Array<{ id?: string; source?: "core" | "plugin" | "channel" }>;
        }>;
      }>(ws, "tools.effective", { sessionKey });

      expect(res.ok).toBe(true);
      expect(res.payload?.agentId).toBeTruthy();
      expect((res.payload?.groups ?? []).length).toBeGreaterThan(0);
      expect(
        (res.payload?.groups ?? []).some((group) =>
          (group.tools ?? []).some((tool) => tool.id === "exec"),
        ),
      ).toBe(true);
    });
  });

  it("rejects unknown agent ids", async () => {
    await withServer(async (ws) => {
      await connectOk(ws, { token: "secret", scopes: ["operator.read", "operator.write"] });
      const created = await rpcReq<{ key?: string }>(ws, "sessions.create", {
        label: "Tools Effective Test",
      });
      expect(created.ok).toBe(true);
      const unknownAgent = await rpcReq(ws, "tools.effective", {
        sessionKey: created.payload?.key,
        agentId: "does-not-exist",
      });
      expect(unknownAgent.ok).toBe(false);
      expect(unknownAgent.error?.message ?? "").toContain("unknown agent id");
    });
  });

  it("nodes-tool: notify requires title or body", async () => {
    const tool = createNodesTool({});
    await expect(tool.execute("call-3", { action: "notify", node: "node-1" })).rejects.toThrow(
      /title or body required/,
    );
  });


  it("nodes-tool: invoke with pairing required error shows approve hint", async () => {
    const tool = createNodesTool({});
    // Spy on resolveNodeId used internally to simulate a pairing-required error that contains a requestId.
    const spy = vi
      .spyOn(await import("../agents/tools/nodes-utils.js"), "resolveNodeId")
      .mockRejectedValue(new Error("Pairing required (requestId: REQ123)"));
    try {
      await expect(
        tool.execute("call-2", { action: "invoke", node: "node-1", invokeCommand: "do.something" }),
      ).rejects.toThrow(/pairing required before node invoke/i);
      await expect(
        tool.execute("call-2", { action: "invoke", node: "node-1", invokeCommand: "do.something" }),
      ).rejects.toThrow(/REQ123/);
    } finally {
      spy.mockRestore();
    }
  });


  it("nodes-tool: unknown action results in wrapped Unknown action error", async () => {
    const tool = createNodesTool({});
    // Execute with a non-existent action; the tool should throw and the error message
    // should include the original "Unknown action" text (wrapped with context).
    await expect(tool.execute("call-1", { action: "nope" })).rejects.toThrow(/Unknown action: nope/);
  });

});
