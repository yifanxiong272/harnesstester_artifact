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







  __testAugmentVitest_1a4ccbe83779.it("user_tool_result_followed_by_image_creates_tool_and_user_round_012_pass_02", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// Tool result + image part should prevent merging into last tool message even when mergeToolResultText=true
  	const messages = [
  		{
  			role: "user",
  			content: [
  				{ type: "tool_result", tool_use_id: "tX", content: "ok" },
  				{ type: "image", source: { media_type: "image/gif", data: "CCC" } },
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages, { mergeToolResultText: true })

  	// Should produce a tool message first, then a separate user message containing the image_url
  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(2)
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].role).toBe("tool")
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].tool_call_id).toBe("tX")
  	__testAugmentVitest_1a4ccbe83779.expect(out[1].role).toBe("user")
  	// The user message content should be an array containing the image_url part
  	__testAugmentVitest_1a4ccbe83779.expect(Array.isArray(out[1].content)).toBe(true)
  	const parts: any[] = out[1].content as any[]
  	__testAugmentVitest_1a4ccbe83779.expect(parts.some(p => p.type === "image_url")).toBe(true)
  	__testAugmentVitest_1a4ccbe83779.expect(parts.find(p => p.type === "image_url").image_url.url).toBe("data:image/gif;base64,CCC")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
