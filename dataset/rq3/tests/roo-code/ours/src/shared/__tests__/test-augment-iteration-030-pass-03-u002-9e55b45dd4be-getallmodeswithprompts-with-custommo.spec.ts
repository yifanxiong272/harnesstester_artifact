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





	  __testAugmentVitest_ec2956a2e658.it("getAllModesWithPrompts_with_customModes_but_no_prompts_round_030_pass_03", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getAllModesWithPrompts } = m

	  	// Create fake context where customModes is present but customModePrompts is missing/empty
	  	const customModes = [
	  		{ slug: "cm-1", name: "CM1", roleDefinition: "CM1 Role", groups: ["read"] },
	  	]

	  	const fakeContext = {
	  		globalState: {
	  			get: async (key: string) => {
	  				if (key === "customModes") return customModes
	  				if (key === "customModePrompts") return {} // explicit empty prompts map
	  				return undefined
	  			},
	  		},
	  	} as any

	  	const all = await getAllModesWithPrompts(fakeContext)
	  	// Find our custom mode
	  	const found = all.find((x) => x.slug === "cm-1")!
	  	// Since there were no prompts for it, the returned roleDefinition should come from the customModes entry
	  	__testAugmentVitest_ec2956a2e658.expect(found.roleDefinition).toBe("CM1 Role")
	  	// whenToUse and customInstructions should fall back to mode values (undefined => empty string not applied here because function returns values or original)
	  	__testAugmentVitest_ec2956a2e658.expect(found.customInstructions).toBe(customModes[0].customInstructions || undefined)
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
