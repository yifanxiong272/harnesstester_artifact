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





	  __testAugmentVitest_ec2956a2e658.it("getAllModes_returns_copy_when_no_custom_round_030_pass_02", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getAllModes, modes } = m

	  	// When no custom modes provided (undefined)
	  	const got1 = getAllModes(undefined)
	  	__testAugmentVitest_ec2956a2e658.expect(got1).toEqual(modes)
	  	__testAugmentVitest_ec2956a2e658.expect(got1).not.toBe(modes) // must be a shallow copy

	  	// When empty array provided
	  	const got2 = getAllModes([])
	  	__testAugmentVitest_ec2956a2e658.expect(got2).toEqual(modes)
	  	__testAugmentVitest_ec2956a2e658.expect(got2).not.toBe(modes)
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
