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







  __testAugmentVitest_1a4ccbe83779.it("user_array_converts_text_image_tool_result_round_010", async () => {
  	// Load target exports
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// Build an Anthropic-style user message with text, image and a tool_result
  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{ type: "text", text: "hello" },
  				{ type: "image", source: { media_type: "image/png", data: "abcd" } },
  				{ type: "tool_result", tool_use_id: "t1", content: "tool output" },
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages)

  	// Expect a tool message first
  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(2)
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].role).toBe("tool")
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].tool_call_id).toBe("t1")
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].content).toBe("tool output")

  	// Expect a user message with text then image_url data URI
  	__testAugmentVitest_1a4ccbe83779.expect(out[1].role).toBe("user")
  	__testAugmentVitest_1a4ccbe83779.expect(Array.isArray(out[1].content)).toBe(true)
  	const userParts: any[] = out[1].content
  	__testAugmentVitest_1a4ccbe83779.expect(userParts[0]).toMatchObject({ type: "text", text: "hello" })
  	__testAugmentVitest_1a4ccbe83779.expect(userParts[1]).toMatchObject({ type: "image_url" })
  	__testAugmentVitest_1a4ccbe83779.expect(userParts[1].image_url.url).toBe("data:image/png;base64,abcd")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
