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







  __testAugmentVitest_1a4ccbe83779.it("user_array_then_string_appends_text_part_round_010_pass_03", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{ type: "image", source: { media_type: "image/png", data: "imgA" } },
  			],
  		},
  		{ role: "user", content: "appended text" },
  	]

  	const out = convertToZAiFormat(messages)

  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	const u = out[0]
  	__testAugmentVitest_1a4ccbe83779.expect(u.role).toBe("user")
  	__testAugmentVitest_1a4ccbe83779.expect(Array.isArray(u.content)).toBe(true)
  	const parts: any[] = u.content
  	// original image converted
  	__testAugmentVitest_1a4ccbe83779.expect(parts[0]).toMatchObject({ type: "image_url" })
  	__testAugmentVitest_1a4ccbe83779.expect(parts[0].image_url.url).toBe("data:image/png;base64,imgA")
  	// appended text should be added as a text part
  	__testAugmentVitest_1a4ccbe83779.expect(parts[1]).toMatchObject({ type: "text", text: "appended text" })
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
