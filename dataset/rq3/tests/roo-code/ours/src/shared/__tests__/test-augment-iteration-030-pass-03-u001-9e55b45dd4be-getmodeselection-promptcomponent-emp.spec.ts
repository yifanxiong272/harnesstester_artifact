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





	  __testAugmentVitest_ec2956a2e658.it("getModeSelection_promptComponent_empty_fallback_round_030_pass_03", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getModeSelection, modes } = m

	  	// Choose a built-in mode to use as base
	  	const base = modes.find((x: any) => !!x.slug)!
	  	// Provide a promptComponent that intentionally has empty strings (falsy) so fallbacks are used
	  	const promptComponent = { roleDefinition: "", customInstructions: "" }

	  	const selection = getModeSelection(base.slug, promptComponent, undefined)

	  	// Because promptComponent fields are empty (falsy), base mode values should be used
	  	__testAugmentVitest_ec2956a2e658.expect(selection.roleDefinition).toBe(base.roleDefinition)
	  	__testAugmentVitest_ec2956a2e658.expect(selection.baseInstructions).toBe(base.customInstructions || "")
	  	__testAugmentVitest_ec2956a2e658.expect(selection.description).toBe(base.description || "")
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
