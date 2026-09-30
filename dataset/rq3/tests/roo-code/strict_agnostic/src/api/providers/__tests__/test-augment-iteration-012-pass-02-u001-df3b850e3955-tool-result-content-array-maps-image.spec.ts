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







  __testAugmentVitest_1a4ccbe83779.it("tool_result_content_array_maps_image_marker_round_012_pass_02", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// A user message with a tool_result whose content is an array with a text and an image
  	const messages = [
  		{
  			role: "user",
  			content: [
  				{
  					type: "tool_result",
  					tool_use_id: "tr1",
  					content: [
  						{ type: "text", text: "partA" },
  						{ type: "image", source: { media_type: "image/jpeg", data: "BBB" } },
  					],
  				},
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages, {})

  	// Should produce a single tool message with content joined: text + newline + (image)
  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	const tm: any = out[0]
  	__testAugmentVitest_1a4ccbe83779.expect(tm.role).toBe("tool")
  	__testAugmentVitest_1a4ccbe83779.expect(tm.tool_call_id).toBe("tr1")
  	__testAugmentVitest_1a4ccbe83779.expect(tm.content).toBe("partA\n(image)")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
