import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ACPX_BUNDLED_BIN,
  ACPX_PINNED_VERSION,
  createAcpxPluginConfigSchema,
  resolveAcpxPluginRoot,
  resolveAcpxPluginConfig,
} from "./config.js";
import * as cs from "../../../src/agents/pi-extensions/compaction-safeguard";

describe("acpx plugin config parsing", () => {
  it("resolves source-layout plugin root from a file under src", () => {
    const pluginRoot = fs.mkdtempSync(path.join(os.tmpdir(), "acpx-root-source-"));
    try {
      fs.mkdirSync(path.join(pluginRoot, "src"), { recursive: true });
      fs.writeFileSync(path.join(pluginRoot, "package.json"), "{}\n", "utf8");
      fs.writeFileSync(path.join(pluginRoot, "openclaw.plugin.json"), "{}\n", "utf8");

      const moduleUrl = pathToFileURL(path.join(pluginRoot, "src", "config.ts")).href;
      expect(resolveAcpxPluginRoot(moduleUrl)).toBe(pluginRoot);
    } finally {
      fs.rmSync(pluginRoot, { recursive: true, force: true });
    }
  });

  it("resolves bundled-layout plugin root from the dist entry file", () => {
    const pluginRoot = fs.mkdtempSync(path.join(os.tmpdir(), "acpx-root-dist-"));
    try {
      fs.writeFileSync(path.join(pluginRoot, "package.json"), "{}\n", "utf8");
      fs.writeFileSync(path.join(pluginRoot, "openclaw.plugin.json"), "{}\n", "utf8");

      const moduleUrl = pathToFileURL(path.join(pluginRoot, "index.js")).href;
      expect(resolveAcpxPluginRoot(moduleUrl)).toBe(pluginRoot);
    } finally {
      fs.rmSync(pluginRoot, { recursive: true, force: true });
    }
  });

  it("prefers the workspace plugin root for dist/extensions/acpx bundles", () => {
    const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "acpx-root-workspace-"));
    const workspacePluginRoot = path.join(repoRoot, "extensions", "acpx");
    const bundledPluginRoot = path.join(repoRoot, "dist", "extensions", "acpx");
    try {
      fs.mkdirSync(workspacePluginRoot, { recursive: true });
      fs.mkdirSync(bundledPluginRoot, { recursive: true });
      fs.writeFileSync(path.join(workspacePluginRoot, "package.json"), "{}\n", "utf8");
      fs.writeFileSync(path.join(workspacePluginRoot, "openclaw.plugin.json"), "{}\n", "utf8");
      fs.writeFileSync(path.join(bundledPluginRoot, "package.json"), "{}\n", "utf8");
      fs.writeFileSync(path.join(bundledPluginRoot, "openclaw.plugin.json"), "{}\n", "utf8");

      const moduleUrl = pathToFileURL(path.join(bundledPluginRoot, "index.js")).href;
      expect(resolveAcpxPluginRoot(moduleUrl)).toBe(workspacePluginRoot);
    } finally {
      fs.rmSync(repoRoot, { recursive: true, force: true });
    }
  });

  it("resolves bundled acpx with pinned version by default", () => {
    const resolved = resolveAcpxPluginConfig({
      rawConfig: {
        cwd: "/tmp/workspace",
      },
      workspaceDir: "/tmp/workspace",
    });

    expect(resolved.command).toBe(ACPX_BUNDLED_BIN);
    expect(resolved.expectedVersion).toBe(ACPX_PINNED_VERSION);
    expect(resolved.allowPluginLocalInstall).toBe(true);
    expect(resolved.stripProviderAuthEnvVars).toBe(true);
    expect(resolved.cwd).toBe(path.resolve("/tmp/workspace"));
    expect(resolved.strictWindowsCmdWrapper).toBe(true);
  });

  it("accepts command override and disables plugin-local auto-install", () => {
    const command = "/home/user/repos/acpx/dist/cli.js";
    const resolved = resolveAcpxPluginConfig({
      rawConfig: {
        command,
      },
      workspaceDir: "/tmp/workspace",
    });

    expect(resolved.command).toBe(path.resolve(command));
    expect(resolved.expectedVersion).toBeUndefined();
    expect(resolved.allowPluginLocalInstall).toBe(false);
    expect(resolved.stripProviderAuthEnvVars).toBe(false);
  });

  it("resolves relative command paths against workspace directory", () => {
    const resolved = resolveAcpxPluginConfig({
      rawConfig: {
        command: "../acpx/dist/cli.js",
      },
      workspaceDir: "/home/user/repos/openclaw",
    });

    expect(resolved.command).toBe(path.resolve("/home/user/repos/openclaw", "../acpx/dist/cli.js"));
    expect(resolved.expectedVersion).toBeUndefined();
    expect(resolved.allowPluginLocalInstall).toBe(false);
    expect(resolved.stripProviderAuthEnvVars).toBe(false);
  });

  it("keeps bare command names as-is", () => {
    const resolved = resolveAcpxPluginConfig({
      rawConfig: {
        command: "acpx",
      },
      workspaceDir: "/tmp/workspace",
    });

    expect(resolved.command).toBe("acpx");
    expect(resolved.expectedVersion).toBeUndefined();
    expect(resolved.allowPluginLocalInstall).toBe(false);
    expect(resolved.stripProviderAuthEnvVars).toBe(false);
  });

  it("accepts exact expectedVersion override", () => {
    const command = "/home/user/repos/acpx/dist/cli.js";
    const resolved = resolveAcpxPluginConfig({
      rawConfig: {
        command,
        expectedVersion: "0.1.99",
      },
      workspaceDir: "/tmp/workspace",
    });

    expect(resolved.command).toBe(path.resolve(command));
    expect(resolved.expectedVersion).toBe("0.1.99");
    expect(resolved.allowPluginLocalInstall).toBe(false);
    expect(resolved.stripProviderAuthEnvVars).toBe(false);
  });

  it("treats expectedVersion=any as no version constraint", () => {
    const resolved = resolveAcpxPluginConfig({
      rawConfig: {
        command: "/home/user/repos/acpx/dist/cli.js",
        expectedVersion: "any",
      },
      workspaceDir: "/tmp/workspace",
    });

    expect(resolved.expectedVersion).toBeUndefined();
  });

  it("rejects commandArgs overrides", () => {
    expect(() =>
      resolveAcpxPluginConfig({
        rawConfig: {
          commandArgs: ["--foo"],
        },
        workspaceDir: "/tmp/workspace",
      }),
    ).toThrow("unknown config key: commandArgs");
  });

  it("schema rejects empty cwd", () => {
    const schema = createAcpxPluginConfigSchema();
    if (!schema.safeParse) {
      throw new Error("acpx config schema missing safeParse");
    }
    const parsed = schema.safeParse({ cwd: "   " });

    expect(parsed.success).toBe(false);
  });

  it("accepts strictWindowsCmdWrapper override", () => {
    const resolved = resolveAcpxPluginConfig({
      rawConfig: {
        strictWindowsCmdWrapper: true,
      },
      workspaceDir: "/tmp/workspace",
    });

    expect(resolved.strictWindowsCmdWrapper).toBe(true);
  });

  it("rejects non-boolean strictWindowsCmdWrapper", () => {
    expect(() =>
      resolveAcpxPluginConfig({
        rawConfig: {
          strictWindowsCmdWrapper: "yes",
        },
        workspaceDir: "/tmp/workspace",
      }),
    ).toThrow("strictWindowsCmdWrapper must be a boolean");
  });

  it("keeps the runtime json schema in sync with the manifest config schema", () => {
    const manifest = JSON.parse(
      fs.readFileSync(new URL("../openclaw.plugin.json", import.meta.url), "utf8"),
    ) as { configSchema?: unknown };

    expect(createAcpxPluginConfigSchema().jsonSchema).toEqual(manifest.configSchema);
  });

  it("compaction-safeguard: collectToolFailures basic normalization and formatToolFailuresSection overflow", () => {
    const t = cs.__testing;
    const messages: any[] = [
      // An error with details but no printable content -> summary should be "failed"
      {
        role: "toolResult",
        toolCallId: "id1",
        toolName: "   ",
        content: undefined,
        details: { status: "crash", exitCode: 2 },
        isError: true,
      },
      // Duplicate toolCallId must be ignored
      {
        role: "toolResult",
        toolCallId: "id1",
        toolName: "dup",
        content: "ignored",
        isError: true,
      },
      // Non-error toolResult should be skipped
      {
        role: "toolResult",
        toolCallId: "id-ok",
        toolName: "oktool",
        content: "ok",
        isError: false,
      },
    ];
    const failures = t.collectToolFailures(messages as any);
    expect(failures.length).toBe(1);
    const f = failures[0];
    expect(f.toolCallId).toBe("id1");
    // blank toolName => fallback to "tool"
    expect(f.toolName).toBe("tool");
    // meta string should include both parts
    expect(f.meta).toBe("status=crash exitCode=2");
    // no printable content but meta present -> "failed"
    expect(f.summary).toBe("failed");
  
    // Build many fake failures to hit overflow path in formatToolFailuresSection
    const manyFailures = Array.from({ length: 10 }, (_, i) => ({
      toolCallId: `t${i}`,
      toolName: `tool-${i}`,
      summary: `err-${i}`,
      meta: i % 2 === 0 ? `status=${i}` : undefined,
    }));
    const section = t.formatToolFailuresSection(manyFailures as any);
    expect(section.includes("## Tool Failures")).toBe(true);
    // Because MAX_TOOL_FAILURES internal limit is 8, overflow indicator should appear
    expect(section.includes("...and")).toBe(true);
  });


  it("compaction-safeguard: formats file operations and handles overflow", () => {
    const t = cs.__testing;
    const { formatFileOperations, MAX_FILE_OPS_LIST_CHARS, MAX_FILE_OPS_SECTION_CHARS } = t;
  
    // empty input -> empty output
    expect(formatFileOperations([], [])).toBe("");
  
    // small lists are rendered with tags
    const small = formatFileOperations(["a.txt", "b.txt"], ["c.txt"]);
    expect(small.includes("<read-files>")).toBe(true);
    expect(small.includes("<modified-files>")).toBe(true);
  
    // build long names to force overflow of the per-list budget
    const longNames: string[] = [];
    // push until we are certain the list length will exceed the per-list char cap
    for (let i = 0; i < 200; i++) {
      longNames.push(`long-name-${i}-${"x".repeat(80)}`);
    }
    const overflow = formatFileOperations(longNames, []);
    // must include overflow indicator
    expect(overflow.includes("...and")).toBe(true);
    // ensure the final section is not larger than the configured section cap
    expect(overflow.length).toBeLessThanOrEqual(MAX_FILE_OPS_SECTION_CHARS);
  });


  it("compaction-safeguard: caps summaries and preserves suffix correctly", () => {
    const t = cs.__testing;
    const { capCompactionSummary, capCompactionSummaryPreservingSuffix, SUMMARY_TRUNCATED_MARKER } =
      t;
  
    // short stays unchanged
    const short = "hello";
    expect(capCompactionSummary(short, 10)).toBe(short);
  
    // long gets the truncation marker when budget allows marker to be appended
    const long = "x".repeat(200);
    const markerBudget = SUMMARY_TRUNCATED_MARKER.length + 10;
    const cappedWithMarker = capCompactionSummary(long, markerBudget);
    expect(cappedWithMarker.includes(SUMMARY_TRUNCATED_MARKER)).toBe(true);
    expect(cappedWithMarker.length).toBeLessThanOrEqual(markerBudget);
  
    // if maxChars less than or equal marker length, we return plain slice without marker
    const tiny = capCompactionSummary(long, 5);
    expect(tiny.length).toBe(5);
    expect(tiny.includes(SUMMARY_TRUNCATED_MARKER)).toBe(false);
  
    // preserving suffix: ensure suffix is kept at the end when space is tight
    const body = "A".repeat(100);
    const suffix = "TAIL";
    const preserved = capCompactionSummaryPreservingSuffix(body, suffix, 10);
    expect(preserved.endsWith(suffix)).toBe(true);
  
    // if suffix is longer than budget, only keep trailing slice of suffix
    const bigSuffix = "S".repeat(20);
    const result = capCompactionSummaryPreservingSuffix(body, bigSuffix, 10);
    expect(result).toBe(bigSuffix.slice(-10));
  
    // empty suffix delegates to regular cap
    expect(capCompactionSummaryPreservingSuffix("abc", "", 2)).toBe(
      capCompactionSummary("abc", 2),
    );
  });


  it("compaction-safeguard: resolves recent turns and quality retries bounds", () => {
    const t = cs.__testing;
    // recent turns: default when undefined
    expect(t.resolveRecentTurnsPreserve(undefined)).toBe(3);
    // negative values clamp to 0
    expect(t.resolveRecentTurnsPreserve(-1)).toBe(0);
    // very large values clamp to MAX_RECENT_TURNS_PRESERVE (12)
    expect(t.resolveRecentTurnsPreserve(1000)).toBe(12);
    // fractional values are floored
    expect(t.resolveRecentTurnsPreserve(2.9)).toBe(2);
  
    // quality guard retries similar behavior
    expect(t.resolveQualityGuardMaxRetries(undefined)).toBe(1);
    expect(t.resolveQualityGuardMaxRetries(-5)).toBe(0);
    expect(t.resolveQualityGuardMaxRetries(100)).toBe(3);
    expect(t.resolveQualityGuardMaxRetries(2.7)).toBe(2);
  });

});
