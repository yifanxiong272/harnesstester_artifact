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







  __testAugmentVitest_1a4ccbe83779.it("assistant_merge_with_previous_assistant_round_010", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// Two assistant messages: first simple string content, second with an array of text parts
  	const messages: any[] = [
  		{ role: "assistant", content: "Hello" },
  		{ role: "assistant", content: [{ type: "text", text: "World" }] },
  	]

  	const out = convertToZAiFormat(messages)

  	// Because the second assistant has no tool_calls, it should merge with the previous assistant
  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].role).toBe("assistant")
  	__testAugmentVitest_1a4ccbe83779.expect(out[0].content).toBe("Hello\nWorld")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
