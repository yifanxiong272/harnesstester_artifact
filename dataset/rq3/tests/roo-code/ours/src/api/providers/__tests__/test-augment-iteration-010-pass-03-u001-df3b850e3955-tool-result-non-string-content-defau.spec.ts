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







  __testAugmentVitest_1a4ccbe83779.it("tool_result_non_string_content_defaults_empty_round_010_pass_03", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{ type: "tool_result", tool_use_id: "t-ns", content: 12345 }, // non-string, non-array
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages)

  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].role).toBe("tool")
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].tool_call_id).toBe("t-ns")
  	// content should fall back to empty string when not string or array
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].content).toBe("")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
