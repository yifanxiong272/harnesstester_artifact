import { describe, expect, it } from "vitest";
import { connectOk, installGatewayTestHooks, rpcReq } from "./test-helpers.js";
import { withServer } from "./test-with-server.js";
import { resolveToolPathAgainstWorkspaceRoot, wrapToolMemoryFlushAppendOnlyWrite } from "../agents/pi-tools.read.js";
import path from "node:path";

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

  it("resolveToolPathAgainstWorkspaceRoot maps paths with relative, absolute and @ prefixes and containerWorkdir", async () => {
    const root = path.resolve("test-workspace-root");
    // Relative path -> resolved against workspace root
    const r1 = resolveToolPathAgainstWorkspaceRoot({ filePath: "sub/file.txt", root });
    expect(r1).toBe(path.resolve(root, "sub", "file.txt"));
  
    // Absolute path -> resolved as absolute
    const absoluteCandidate = path.resolve("/", "tmp", "absfile.txt");
    const r2 = resolveToolPathAgainstWorkspaceRoot({ filePath: absoluteCandidate, root });
    expect(r2).toBe(path.resolve(absoluteCandidate));
  
    // Leading '@' stripped and treated as relative
    const r3 = resolveToolPathAgainstWorkspaceRoot({ filePath: "@other.txt", root });
    expect(r3).toBe(path.resolve(root, "other.txt"));
  
    // containerWorkdir maps container-internal absolute path to workspace relative path
    const containerWorkdir = "/app/work";
    const containerFile = "/app/work/sub/a.txt";
    const r4 = resolveToolPathAgainstWorkspaceRoot({
      filePath: containerFile,
      root,
      containerWorkdir,
    });
    expect(r4).toBe(path.resolve(root, "sub", "a.txt"));
  });


  it("appends content to memory flush file via sandbox bridge and rejects other paths", async () => {
    const calls: {
      wrote?: { filePath: string; cwd: string; data: string };
      mkdirpCalled?: boolean;
    } = {};
    // A minimal sandbox bridge implementation to capture interactions
    const bridge = {
      stat: async ({ filePath }: { filePath: string }) => {
        // No existing file: return null to signal "not found"
        return null;
      },
      readFile: async ({ filePath }: { filePath: string }) => {
        // Should not be called in this scenario because stat returned null; but implement anyway
        return Buffer.from("");
      },
      mkdirp: async ({ filePath }: { filePath: string }) => {
        calls.mkdirpCalled = true;
      },
      writeFile: async ({ filePath, cwd, data }: { filePath: string; cwd: string; data: string }) => {
        calls.wrote = { filePath, cwd, data };
      },
    };
    const workspaceRoot = path.resolve("/workspace");
    const options = {
      root: workspaceRoot,
      relativePath: "memory.txt",
      sandbox: {
        root: workspaceRoot,
        bridge,
      },
    };
    // Base tool is not used for the append case, but provide a minimal tool object
    const baseTool = {
      name: "test-tool",
      description: "base",
      execute: async () => ({ content: [] as unknown[] }),
    } as const;
    const wrapped = wrapToolMemoryFlushAppendOnlyWrite(baseTool as any, options as any);
    // Allowed path: should trigger append through the sandbox bridge
    const result = await wrapped.execute("call-1", { path: "memory.txt", content: "hello world" });
    expect(calls.wrote).toBeTruthy();
    expect(calls.wrote?.filePath).toBe("memory.txt");
    expect(calls.wrote?.cwd).toBe(workspaceRoot);
    expect(calls.wrote?.data).toContain("hello world");
    // Verify the wrapper returned the expected result shape
    expect(result.content && Array.isArray(result.content)).toBe(true);
    expect((result.content?.[0] as any)?.text).toContain("Appended content to memory.txt.");
    expect((result.details as any)?.path).toBe("memory.txt");
    expect((result.details as any)?.appendOnly).toBe(true);
    // Disallowed path: should throw because resolved path is not the allowedAbsolutePath
    await expect(
      wrapped.execute("call-2", { path: "other-file.txt", content: "x" }),
    ).rejects.toThrow();
  });


  it("resolves tool paths relative and absolute", async () => {
    // static imports in new_imports_code provide the function and path
    const root = path.resolve("/tmp/workspace-root");
    // relative path should resolve against the provided root
    const rel = resolveToolPathAgainstWorkspaceRoot({ filePath: "foo.txt", root });
    expect(rel).toBe(path.resolve(root, "foo.txt"));
    // absolute path should be returned as an absolute resolved path
    const abs = resolveToolPathAgainstWorkspaceRoot({ filePath: "/var/data/config.json", root });
    expect(abs).toBe(path.resolve("/var/data/config.json"));
    // an empty candidate should resolve to the workspace root
    const empty = resolveToolPathAgainstWorkspaceRoot({ filePath: "", root });
    expect(empty).toBe(path.resolve(root, "."));
  });

});
