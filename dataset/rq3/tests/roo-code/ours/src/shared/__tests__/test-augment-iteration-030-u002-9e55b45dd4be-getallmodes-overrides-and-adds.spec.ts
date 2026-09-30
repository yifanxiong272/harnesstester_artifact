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





	  __testAugmentVitest_ec2956a2e658.it("getAllModes_overrides_and_adds_round_030", async () => {
	  	const m = await __testAugmentLoadTarget_7e3031a9c72e()
	  	const { getAllModes, modes } = m

	  	// Prepare an override of the first built-in mode and a completely new custom mode
	  	const base = modes[0]
	  	const override = {
	  		...base,
	  		name: "Overridden Mode Name",
	  		roleDefinition: "Overridden Role",
	  		// keep slug identical to override built-in behavior
	  		slug: base.slug,
	  		groups: base.groups || ["read"],
	  	}
	  	const added = {
	  		slug: "brand-new-mode",
	  		name: "Brand New Mode",
	  		roleDefinition: "BN Role",
	  		groups: ["read"],
	  		customInstructions: "BN Instructions",
	  	}

	  	const result = getAllModes([override, added])

	  	// The override should replace built-in mode with same slug
	  	__testAugmentVitest_ec2956a2e658.expect(result.find((r) => r.slug === base.slug)?.name).toBe("Overridden Mode Name")
	  	// The new mode should appear in the result
	  	__testAugmentVitest_ec2956a2e658.expect(result.find((r) => r.slug === "brand-new-mode")).toBeDefined()
	  	// Because one new mode was added, total length should be original + 1
	  	__testAugmentVitest_ec2956a2e658.expect(result.length).toBe(modes.length + 1)
	  })
	})


})


import * as __testAugmentVitest_ec2956a2e658 from "vitest";

const __testAugmentLoadTarget_7e3031a9c72e = async () => {
  __testAugmentVitest_ec2956a2e658.vi.doUnmock("../modes.js");
  __testAugmentVitest_ec2956a2e658.vi.resetModules();
  return import("../modes.js");
};
