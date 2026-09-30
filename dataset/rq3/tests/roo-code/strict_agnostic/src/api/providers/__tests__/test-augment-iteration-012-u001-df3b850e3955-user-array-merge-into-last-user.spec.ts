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







  __testAugmentVitest_1a4ccbe83779.it("user_array_and_merge_with_previous_user_round_012", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// First a simple user message (string content), then a user message with text+image parts.
  	const messages = [
  		{ role: "user", content: "first" },
  		{
  			role: "user",
  			content: [
  				{ type: "text", text: "second" },
  				{ type: "image", source: { media_type: "image/png", data: "AAA" } },
  			],
  		},
  	]

  	const result = convertToZAiFormat(messages, {})

  	// The second message should merge into the previous user message, producing an array of parts
  	__testAugmentVitest_1a4ccbe83779.expect(result.length).toBe(1)
  	__testAugmentVitest_1a4ccbe83779.expect(result[0].role).toBe("user")
  	__testAugmentVitest_1a4ccbe83779.expect(Array.isArray(result[0].content)).toBe(true)

  	// After merging, the first element should be the original 'first' text turned into a text part
  	const contents: any[] = result[0].content as any[]
  	__testAugmentVitest_1a4ccbe83779.expect(contents[0]).toEqual({ type: "text", text: "first" })
  	// Next should be the new text part
  	__testAugmentVitest_1a4ccbe83779.expect(contents[1]).toEqual({ type: "text", text: "second" })
  	// And finally the image was converted to image_url format and preserved
  	__testAugmentVitest_1a4ccbe83779.expect(contents[2]).toHaveProperty("type", "image_url")
  	__testAugmentVitest_1a4ccbe83779.expect(contents[2]).toHaveProperty("image_url")
  	__testAugmentVitest_1a4ccbe83779.expect((contents[2] as any).image_url.url).toBe("data:image/png;base64,AAA")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
