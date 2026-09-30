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







  __testAugmentVitest_1a4ccbe83779.it("user_merge_into_last_tool_round_010", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// A user message where a tool_result is followed by text; enable mergeToolResultText
  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{ type: "tool_result", tool_use_id: "t1", content: "tool content" },
  				{ type: "text", text: "extra text" },
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages, { mergeToolResultText: true })

  	// When mergeToolResultText is enabled and there are toolResults and no images,
  	// the text should be merged into the last tool message rather than creating a user message.
  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].role).toBe("tool")
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].tool_call_id).toBe("t1")
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].content).toBe("tool content\n\nextra text")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
