// npx vitest run core/prompts/tools/__tests__/filter-tools-for-mode.spec.ts

import type OpenAI from "openai"

import { filterNativeToolsForMode } from "../filter-tools-for-mode"

function makeTool(name: string): OpenAI.Chat.ChatCompletionTool {
	return {
		type: "function",
		function: {
			name,
			description: `${name} tool`,
			parameters: { type: "object", properties: {} },
		},
	} as OpenAI.Chat.ChatCompletionTool
}

describe("filterNativeToolsForMode - disabledTools", () => {
	const nativeTools: OpenAI.Chat.ChatCompletionTool[] = [
		makeTool("execute_command"),
		makeTool("read_file"),
		makeTool("write_to_file"),
		makeTool("apply_diff"),
		makeTool("edit"),
	]





  __testAugmentVitest_c5f7390aae83.it("renames native tool to alias and caches_round_022", async () => {
  	// Provide aliases and a tool group so model-included alias can be resolved to canonical 'edit'
  	__testAugmentVitest_c5f7390aae83.vi.doMock("../../../shared/tools", () => ({
  		TOOL_ALIASES: { "search_and_replace": "edit" },
  		TOOL_GROUPS: { editing: { tools: ["edit"], customTools: [] } },
  		ALWAYS_AVAILABLE_TOOLS: [],
  	}))
  	// Provide minimal mode helpers used by filterNativeToolsForMode
  	__testAugmentVitest_c5f7390aae83.vi.doMock("../../../shared/modes", () => ({
  		getModeBySlug: (_slug: any, _custom: any) => ({ groups: ["editing"] }),
  		getToolsForMode: (_groups: any) => ["edit"],
  	}))
  	// Make permission checks always pass for this test
  	__testAugmentVitest_c5f7390aae83.vi.doMock("../../../core/tools/validateToolUse", () => ({
  		isToolAllowedForMode: () => true,
  	}))

  	const { filterNativeToolsForMode } = await __testAugmentLoadTarget_2ee949f887fb()

  	const nativeTools = [
  		{
  			type: "function",
  			function: { name: "edit", description: "edit tool", parameters: { type: "object", properties: {} } },
  		},
  	]

  	const settings = { modelInfo: { includedTools: ["search_and_replace"] } }

  	// Call twice to exercise RENAMED_TOOL_CACHE behavior (object identity should be stable)
  	const first = filterNativeToolsForMode(nativeTools as any, "someMode", undefined, {}, undefined, settings)
  	const second = filterNativeToolsForMode(nativeTools as any, "someMode", undefined, {}, undefined, settings)

  	__testAugmentVitest_c5f7390aae83.expect(first.length).toBe(1)
  	// The returned tool should be renamed to the alias specified in modelInfo
  	__testAugmentVitest_c5f7390aae83.expect((first[0] as any).function.name).toBe("search_and_replace")
  	// The cached renamed tool object should be identical between calls
  	__testAugmentVitest_c5f7390aae83.expect(first[0]).toBe(second[0])
  })
})

import * as __testAugmentVitest_c5f7390aae83 from "vitest";

const __testAugmentLoadTarget_2ee949f887fb = async () => {
  __testAugmentVitest_c5f7390aae83.vi.doUnmock("../filter-tools-for-mode.js");
  __testAugmentVitest_c5f7390aae83.vi.resetModules();
  return import("../filter-tools-for-mode.js");
};
