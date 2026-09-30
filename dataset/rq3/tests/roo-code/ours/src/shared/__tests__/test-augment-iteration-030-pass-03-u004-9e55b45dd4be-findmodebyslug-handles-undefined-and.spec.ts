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





	  __testAugmentVitest_ec2956a2e658.it("findModeBySlug_handles_undefined_and_array_round_030_pass_03", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { findModeBySlug } = m

	  	// When modes is undefined, should return undefined
	  	__testAugmentVitest_ec2956a2e658.expect(findModeBySlug("anything", undefined)).toBeUndefined()

	  	// When provided an array, it should return the matching entry
	  	const arr = [
	  		{ slug: "one", name: "One" },
	  		{ slug: "two", name: "Two" },
	  	]
	  	const got = findModeBySlug("two", arr)
	  	__testAugmentVitest_ec2956a2e658.expect(got).toBeDefined()
	  	__testAugmentVitest_ec2956a2e658.expect(got?.slug).toBe("two")
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
