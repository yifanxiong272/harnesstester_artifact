import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";
import { vi } from "vitest";

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

  it("nodes: invoke transforms pairing required errors into pairing hint without requestId", async () => {
    vi.resetModules();
    const callGatewayTool = vi.fn(async (method) => {
      if (method === "node.invoke") {
        throw new Error("Not_paired");
      }
      return {};
    });
    vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool,
      readGatewayCallOptions: () => ({}),
    }));
    const resolveNodeId = vi.fn(async () => "node-xyz");
    vi.doMock("../agents/tools/nodes-utils.js", () => ({ resolveNodeId }));
    const { createNodesTool } = await import("../agents/tools/nodes-tool.js");
    const tool = createNodesTool();
    await expect(
      tool.execute("call-id", { action: "invoke", node: "any", invokeCommand: "custom.cmd" }),
    ).rejects.toThrow(/Approve the pending pairing request and retry/i);
  });


  it("nodes: invoke transforms pairing required errors into pairing hint including requestId", async () => {
    vi.resetModules();
    const callGatewayTool = vi.fn(async (method) => {
      if (method === "node.invoke") {
        throw new Error("Pairing required (requestId: RQ-456)");
      }
      return {};
    });
    vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool,
      readGatewayCallOptions: () => ({}),
    }));
    // resolveNodeId is used to map node param to a node id for 'invoke'
    const resolveNodeId = vi.fn(async () => "node-123");
    vi.doMock("../agents/tools/nodes-utils.js", () => ({ resolveNodeId }));
    const { createNodesTool } = await import("../agents/tools/nodes-tool.js");
    const tool = createNodesTool();
    // The error thrown by the mocked gateway should be caught and transformed to include pairing hint.
    await expect(
      tool.execute("call-id", { action: "invoke", node: "any", invokeCommand: "custom.cmd" }),
    ).rejects.toThrow(/pairing required before node invoke/i);
    await expect(
      tool.execute("call-id", { action: "invoke", node: "any", invokeCommand: "custom.cmd" }),
    ).rejects.toThrow(/RQ-456/);
  });


  it("nodes: approve uses pair.list and calls node.pair.approve with operator.write for custom commands", async () => {
    vi.resetModules();
    const callGatewayTool = vi.fn(async (method) => {
      if (method === "node.pair.list") {
        return { pending: [{ requestId: "REQ-CUSTOM", commands: ["some.custom.command"] }] };
      }
      if (method === "node.pair.approve") {
        return { ok: true };
      }
      return {};
    });
    vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool,
      readGatewayCallOptions: () => ({}),
    }));
    const { createNodesTool } = await import("../agents/tools/nodes-tool.js");
    const tool = createNodesTool();
    const result = await tool.execute("call-id", { action: "approve", requestId: "REQ-CUSTOM" });
    expect(callGatewayTool).toHaveBeenCalled();
    const approveCall = callGatewayTool.mock.calls.find((c) => c[0] === "node.pair.approve");
    expect(approveCall).toBeTruthy();
    const approveOptions = approveCall ? approveCall[3] : undefined;
    expect(approveOptions).toBeTruthy();
    expect(Array.isArray(approveOptions.scopes)).toBe(true);
    expect(approveOptions.scopes).toEqual(["operator.write"]);
    expect(result).toBeDefined();
  });


  it("nodes: approve uses pair.list and calls node.pair.approve with operator.admin", async () => {
    // Use non-hoisted mocks so we can create local mock functions safely per-test.
    vi.resetModules();
    const callGatewayTool = vi.fn(async (method, gatewayOpts, payload, extra) => {
      if (method === "node.pair.list") {
        return { pending: [{ requestId: "REQ-123", commands: ["system.run", "other.cmd"] }] };
      }
      if (method === "node.pair.approve") {
        return { ok: true, approved: true };
      }
      return {};
    });
    vi.doMock("../agents/tools/gateway.js", () => ({
      callGatewayTool,
      readGatewayCallOptions: () => ({}),
    }));
    const { createNodesTool } = await import("../agents/tools/nodes-tool.js");
    const tool = createNodesTool();
    const result = await tool.execute("call-id", { action: "approve", requestId: "REQ-123" });
    // callGatewayTool should have been invoked and node.pair.approve should be among the calls
    expect(callGatewayTool).toHaveBeenCalled();
    const approveCall = callGatewayTool.mock.calls.find((c) => c[0] === "node.pair.approve");
    expect(approveCall).toBeTruthy();
    const approveOptions = approveCall ? approveCall[3] : undefined;
    expect(approveOptions).toBeTruthy();
    expect(Array.isArray(approveOptions.scopes)).toBe(true);
    expect(approveOptions.scopes).toEqual(["operator.admin"]);
    // basic sanity: the tool returned something (jsonResult wrapper)
    expect(result).toBeDefined();
  });

});
