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





	  __testAugmentVitest_ec2956a2e658.it("safe_getters_return_existing_values_round_030_pass_02", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getRoleDefinition, getDescription, getWhenToUse, getCustomInstructions, modes } = m

	  	const someMode = modes.find((x: any) => !!x.slug)!
	  	// Ensure this mode has at least some properties defined to validate returns
	  	__testAugmentVitest_ec2956a2e658.expect(getRoleDefinition(someMode.slug)).toBe(someMode.roleDefinition)
	  	__testAugmentVitest_ec2956a2e658.expect(getDescription(someMode.slug)).toBe(someMode.description ?? "")
	  	__testAugmentVitest_ec2956a2e658.expect(getWhenToUse(someMode.slug)).toBe(someMode.whenToUse ?? "")
	  	__testAugmentVitest_ec2956a2e658.expect(getCustomInstructions(someMode.slug)).toBe(someMode.customInstructions ?? "")
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
