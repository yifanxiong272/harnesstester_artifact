// npx vitest run src/api/providers/__tests__/zai.spec.ts

import OpenAI from "openai"
import { Anthropic } from "@anthropic-ai/sdk"

import {
	type InternationalZAiModelId,
	type MainlandZAiModelId,
	internationalZAiDefaultModelId,
	mainlandZAiDefaultModelId,
	internationalZAiModels,
	mainlandZAiModels,
	ZAI_DEFAULT_TEMPERATURE,
} from "@roo-code/types"

import { ZAiHandler } from "../zai"

vitest.mock("openai", () => {
	const createMock = vitest.fn()
	return {
		default: vitest.fn(() => ({ chat: { completions: { create: createMock } } })),
	}
})

describe("ZAiHandler", () => {
	let handler: ZAiHandler
	let mockCreate: any

	beforeEach(() => {
		vitest.clearAllMocks()
		mockCreate = (OpenAI as unknown as any)().chat.completions.create
	})







  __testAugmentVitest_1a4ccbe83779.it("assistant_prev_array_then_simple_string_coerces_and_appends_round_010_pass_03", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// Previous assistant has an array content (non-string). The implementation string-coerces
  	// lastContent when concatenating, so the array becomes its toString() representation.
  	const messages: any[] = [
  		{ role: "assistant", content: [{ type: "text", text: "X" }] },
  		{ role: "assistant", content: "Y" },
  	]

  	const out = convertToZAiFormat(messages)

  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].role).toBe("assistant")
  	// Implementation currently coerces previous array content to string and appends new string
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].content).toBe("X\nY")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
