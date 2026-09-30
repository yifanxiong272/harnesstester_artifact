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







  __testAugmentVitest_1a4ccbe83779.it("user_merge_array_into_existing_user_string_round_010_pass_02", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	const messages: any[] = [
  		{ role: "user", content: "first-line" },
  		{
  			role: "user",
  			content: [
  				{ type: "text", text: "second-line" },
  				{ type: "image", source: { media_type: "image/jpeg", data: "imgdata" } },
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages)

  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	const user = out[0]
  	__testAugmentVitest_1a4ccbe83779.expect(user.role).toBe("user")
  	__testAugmentVitest_1a4ccbe83779.expect(Array.isArray(user.content)).toBe(true)
  	const parts: any[] = user.content
  	// First part should be the original user text converted to a text-part
  	__testAugmentVitest_1a4ccbe83779.expect(parts[0]).toMatchObject({ type: "text", text: "first-line" })
  	// Next should be the new text part
  	__testAugmentVitest_1a4ccbe83779.expect(parts[1]).toMatchObject({ type: "text", text: "second-line" })
  	// Image should be converted to image_url form
  	__testAugmentVitest_1a4ccbe83779.expect(parts[2]).toMatchObject({ type: "image_url" })
  	__testAugmentVitest_1a4ccbe83779.expect(parts[2].image_url.url).toBe("data:image/jpeg;base64,imgdata")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
