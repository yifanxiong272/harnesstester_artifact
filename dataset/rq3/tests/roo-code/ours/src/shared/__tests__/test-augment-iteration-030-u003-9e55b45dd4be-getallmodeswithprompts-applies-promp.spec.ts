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





	  __testAugmentVitest_ec2956a2e658.it("getAllModesWithPrompts_applies_prompt_overrides_round_030", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getAllModesWithPrompts, modes } = m

	  	// Simulate extension context globalState storing a custom mode and prompt overrides
	  	const customModeSlug = modes[0].slug
	  	const fakeContext = {
	  		globalState: {
	  			get: async (key) => {
	  				if (key === "customModes") {
	  					return [
	  						{
	  							slug: customModeSlug,
	  							name: "Customized Name",
	  							roleDefinition: "Custom RD",
	  							groups: ["read"],
	  						},
	  					]
	  				}
	  				if (key === "customModePrompts") {
	  					return {
	  						[customModeSlug]: {
	  							roleDefinition: "Prompted Role",
	  							whenToUse: "Use when X",
	  							customInstructions: "Prompted instructions",
	  						},
	  					}
	  				}
	  				return undefined
	  			},
	  		},
	  	}

	  	const all = await getAllModesWithPrompts(fakeContext as any)
	  	const found = all.find((x) => x.slug === customModeSlug)!

	  	// RoleDefinition should be taken from customModePrompts if present
	  	__testAugmentVitest_ec2956a2e658.expect(found.roleDefinition).toBe("Prompted Role")
	  	// whenToUse should be taken from customModePrompts
	  	__testAugmentVitest_ec2956a2e658.expect(found.whenToUse).toBe("Use when X")
	  	// customInstructions should be taken from customModePrompts
	  	__testAugmentVitest_ec2956a2e658.expect(found.customInstructions).toBe("Prompted instructions")
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
