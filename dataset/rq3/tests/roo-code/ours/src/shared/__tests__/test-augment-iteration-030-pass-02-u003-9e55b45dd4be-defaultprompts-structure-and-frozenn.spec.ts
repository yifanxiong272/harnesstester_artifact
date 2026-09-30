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





	  __testAugmentVitest_ec2956a2e658.it("defaultPrompts_structure_and_frozenness_round_030_pass_02", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { defaultPrompts, modes } = m

	  	// defaultPrompts should be an object with entries for each built-in mode slug
	  	const first = modes[0]
	  	const entry = (defaultPrompts as any)[first.slug]
	  	__testAugmentVitest_ec2956a2e658.expect(entry).toBeDefined()
	  	__testAugmentVitest_ec2956a2e658.expect(entry.roleDefinition).toBe(first.roleDefinition)
	  	__testAugmentVitest_ec2956a2e658.expect(entry.customInstructions).toBe(first.customInstructions)
	  	__testAugmentVitest_ec2956a2e658.expect(entry.description).toBe(first.description)
	  	__testAugmentVitest_ec2956a2e658.expect(entry.whenToUse).toBe(first.whenToUse)

	  	// The exported defaultPrompts object was frozen via Object.freeze
	  	__testAugmentVitest_ec2956a2e658.expect(Object.isFrozen(defaultPrompts)).toBe(true)
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
