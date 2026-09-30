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







  __testAugmentVitest_1a4ccbe83779.it("assistant_tool_use_and_reasoning_round_010", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// Assistant message that contains a tool_use block and a reasoning block in content array
  	const messages: any[] = [
  		{
  			role: "assistant",
  			content: [
  				{ type: "tool_use", id: "id1", name: "fn", input: { a: 1 } },
  				{ type: "reasoning", text: "thoughts" },
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages)

  	// Should produce an assistant message with tool_calls and preserved reasoning_content
  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	const am = out[0]
  	__testAugmentVitest_1a4ccbe83779.expect(am.role).toBe("assistant")
  	__testAugmentVitest_1a4ccbe83779.expect(am.tool_calls).toBeDefined()
  	__testAugmentVitest_1a4ccbe83779.expect(Array.isArray(am.tool_calls)).toBe(true)
  	__testAugmentVitest_1a4ccbe83779.expect(am.tool_calls[0]).toMatchObject({ id: "id1", type: "function" })
  	__testAugmentVitest_1a4ccbe83779.expect(am.tool_calls[0].function).toMatchObject({ name: "fn" })
  	// arguments should be a JSON string of the input
  	__testAugmentVitest_1a4ccbe83779.expect(am.tool_calls[0].function.arguments).toBe(JSON.stringify({ a: 1 }))
  	__testAugmentVitest_1a4ccbe83779.expect(am.reasoning_content).toBe("thoughts")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
