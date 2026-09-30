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





	  __testAugmentVitest_ec2956a2e658.it("isCustomMode_true_and_false_outcomes_round_030_pass_02", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { isCustomMode } = m

	  	const customModes = [{ slug: "custom-slug", name: "C", roleDefinition: "R", groups: ["read"] }]
	  	__testAugmentVitest_ec2956a2e658.expect(isCustomMode("custom-slug", customModes)).toBe(true)
	  	__testAugmentVitest_ec2956a2e658.expect(isCustomMode("other", customModes)).toBe(false)
	  	// Also verify falsy customModes yields false
	  	__testAugmentVitest_ec2956a2e658.expect(isCustomMode("custom-slug", undefined)).toBe(false)
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
