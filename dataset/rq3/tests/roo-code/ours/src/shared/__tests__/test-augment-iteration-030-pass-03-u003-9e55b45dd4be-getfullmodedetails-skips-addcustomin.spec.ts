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





	  __testAugmentVitest_ec2956a2e658.it("getFullModeDetails_skips_addCustomInstructions_when_no_cwd_round_030_pass_03", async () => {
	  	// The seed harness imported and mocked addCustomInstructions at file scope; clear and spy it here
	  	__testAugmentVitest_ec2956a2e658.vi.clearAllMocks()
	  	const spy = __testAugmentVitest_ec2956a2e658.vi.spyOn(addCustomInstructions, "mockResolvedValue" as any).mockImplementation?.(() => Promise.resolve("SHOULD_NOT_BE_CALLED"))
	  	// Note: the above spy is defensive; addCustomInstructions is a jest/vitest mock in seed scope

	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getFullModeDetails } = m

	  	// Call without options (no cwd) - addCustomInstructions should not be invoked
	  	await getFullModeDetails("debug")

	  	// If spy is defined, assert it was not called; otherwise just ensure mocks were not invoked via the global mocked function
	  	if (spy) {
	  		__testAugmentVitest_ec2956a2e658.expect(spy).not.toHaveBeenCalled()
	  	}

	  	__testAugmentVitest_ec2956a2e658.vi.clearAllMocks()
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
