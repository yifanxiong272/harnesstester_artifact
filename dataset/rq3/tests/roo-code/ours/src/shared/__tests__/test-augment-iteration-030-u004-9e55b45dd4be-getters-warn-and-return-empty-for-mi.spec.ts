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





	  __testAugmentVitest_ec2956a2e658.it("getters_warn_and_return_empty_for_missing_mode_round_030", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getRoleDefinition, getDescription, getWhenToUse, getCustomInstructions } = m

	  	const spy = __testAugmentVitest_ec2956a2e658.vi.spyOn(console, "warn").mockImplementation(() => {})

	  	const missing = "this-mode-does-not-exist"
	  	__testAugmentVitest_ec2956a2e658.expect(getRoleDefinition(missing)).toBe("")
	  	__testAugmentVitest_ec2956a2e658.expect(getDescription(missing)).toBe("")
	  	__testAugmentVitest_ec2956a2e658.expect(getWhenToUse(missing)).toBe("")
	  	__testAugmentVitest_ec2956a2e658.expect(getCustomInstructions(missing)).toBe("")

	  	// Should have warned at least once across the calls
	  	__testAugmentVitest_ec2956a2e658.expect(spy).toHaveBeenCalled()

	  	spy.mockRestore()
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
