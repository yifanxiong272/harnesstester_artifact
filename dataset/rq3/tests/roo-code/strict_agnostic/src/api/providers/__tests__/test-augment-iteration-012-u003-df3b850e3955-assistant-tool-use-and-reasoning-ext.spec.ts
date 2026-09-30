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







  __testAugmentVitest_1a4ccbe83779.it("assistant_tool_use_and_reasoning_extraction_round_012", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// Assistant message containing text, a tool_use block, and an inline reasoning block
  	const messages = [
  		{
  			role: "assistant",
  			content: [
  				{ type: "text", text: "assist text" },
  				{ type: "tool_use", id: "id1", name: "doIt", input: { x: 1 } },
  				{ type: "reasoning", text: "thoughts" },
  			],
  		},
  	]

  	const result = convertToZAiFormat(messages, {})

  	__testAugmentVitest_1a4ccbe83779.expect(result.length).toBe(1)
  	const am: any = result[0]
  	__testAugmentVitest_1a4ccbe83779.expect(am.role).toBe("assistant")
  	// Content should be the joined text parts
  	__testAugmentVitest_1a4ccbe83779.expect(am.content).toBe("assist text")
  	// tool_calls should be present and have function metadata
  	__testAugmentVitest_1a4ccbe83779.expect(Array.isArray(am.tool_calls)).toBe(true)
  	__testAugmentVitest_1a4ccbe83779.expect(am.tool_calls[0].id).toBe("id1")
  	__testAugmentVitest_1a4ccbe83779.expect(am.tool_calls[0].function.name).toBe("doIt")
  	__testAugmentVitest_1a4ccbe83779.expect(am.tool_calls[0].function.arguments).toBe(JSON.stringify({ x: 1 }))
  	// reasoning_content should be preserved from the embedded reasoning block
  	__testAugmentVitest_1a4ccbe83779.expect(am.reasoning_content).toBe("thoughts")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
