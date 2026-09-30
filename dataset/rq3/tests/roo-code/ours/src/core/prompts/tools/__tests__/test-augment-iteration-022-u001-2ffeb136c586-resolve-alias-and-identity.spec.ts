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





  __testAugmentVitest_c5f7390aae83.it("resolve alias and identity_round_022", async () => {
  	// Provide a controlled TOOL_ALIASES so module-level maps are built deterministically
  	__testAugmentVitest_c5f7390aae83.vi.doMock("../../../shared/tools", () => ({
  		TOOL_ALIASES: { "search_and_replace": "edit", "alias1": "canon1" },
  		TOOL_GROUPS: {},
  		ALWAYS_AVAILABLE_TOOLS: [],
  	}))

  	const { resolveToolAlias } = await __testAugmentLoadTarget_2ee949f887fb()

  	// Alias resolves to canonical
  	__testAugmentVitest_c5f7390aae83.expect(resolveToolAlias("search_and_replace")).toBe("edit")
  	// Unknown tool is returned as-is
  	__testAugmentVitest_c5f7390aae83.expect(resolveToolAlias("some_nonexistent_tool")).toBe("some_nonexistent_tool")
  })
})

import * as __testAugmentVitest_c5f7390aae83 from "vitest";

const __testAugmentLoadTarget_2ee949f887fb = async () => {
  __testAugmentVitest_c5f7390aae83.vi.doUnmock("../filter-tools-for-mode.js");
  __testAugmentVitest_c5f7390aae83.vi.resetModules();
  return import("../filter-tools-for-mode.js");
};
