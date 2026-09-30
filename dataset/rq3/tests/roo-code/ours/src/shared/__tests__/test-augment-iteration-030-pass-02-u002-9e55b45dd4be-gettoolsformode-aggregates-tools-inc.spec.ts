// npx vitest run shared/__tests__/modes.spec.ts

import type { ModeConfig, PromptComponent } from "@roo-code/types"

// Mock setup must come before imports
vi.mock("vscode")

vi.mock("../../core/prompts/sections/custom-instructions", () => ({
	addCustomInstructions: vi.fn().mockResolvedValue("Combined instructions"),
}))

import { FileRestrictionError, getFullModeDetails, modes, getModeSelection } from "../modes"
import { isToolAllowedForMode } from "../../core/tools/validateToolUse"
import { addCustomInstructions } from "../../core/prompts/sections/custom-instructions"


describe("FileRestrictionError", () => {



	describe("getFullModeDetails", () => {
		beforeEach(() => {
			vi.clearAllMocks()
			vi.mocked(addCustomInstructions).mockResolvedValue("Combined instructions")
		})





	  __testAugmentVitest_ec2956a2e658.it("getToolsForMode_aggregates_tools_including_always_available_round_030_pass_02", async () => {
	  	// Mock the tools module to control TOOL_GROUPS and ALWAYS_AVAILABLE_TOOLS for deterministic behavior
	  	__testAugmentVitest_ec2956a2e658.vi.doMock("../tools", () => ({
	  		TOOL_GROUPS: {
	  			groupA: { tools: ["tool-a", "shared-tool"] },
	  			groupB: { tools: ["tool-b", "shared-tool"] },
	  		},
	  		ALWAYS_AVAILABLE_TOOLS: ["always-1", "shared-tool"],
	  	}))

	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getToolsForMode } = m

	  	// Provide groups as a mix of string and tuple form; duplicates should be deduped
	  	const groups: any[] = ["groupA", ["groupB", { someOpt: true }]]
	  	const tools = getToolsForMode(groups)

	  	// Ensure all expected tools are present and deduplicated
	  	__testAugmentVitest_ec2956a2e658.expect(tools).toEqual(expect.arrayContaining(["tool-a", "tool-b", "always-1", "shared-tool"]))
	  	// shared-tool should appear only once in the resulting array
	  	const occurrences = tools.filter((t) => t === "shared-tool").length
	  	__testAugmentVitest_ec2956a2e658.expect(occurrences).toBe(1)
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
