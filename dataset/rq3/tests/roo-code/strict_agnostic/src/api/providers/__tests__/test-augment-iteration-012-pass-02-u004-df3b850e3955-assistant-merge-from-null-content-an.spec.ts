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







  __testAugmentVitest_1a4ccbe83779.it("assistant_merge_from_null_content_and_preserve_reasoning_round_012_pass_02", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// First assistant message has empty content array -> produces content: null, no tool_calls
  	// Second assistant message has text parts and top-level reasoning_content
  	const messages = [
  		{ role: "assistant", content: [] },
  		{ role: "assistant", content: [{ type: "text", text: "later" }], reasoning_content: "keep-thoughts" },
  	]

  	const out = convertToZAiFormat(messages, {})

  	// They should merge into one assistant message; null + text yields a string with leading newline
  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	const a: any = out[0]
  	__testAugmentVitest_1a4ccbe83779.expect(a.role).toBe("assistant")
  	__testAugmentVitest_1a4ccbe83779.expect(a.content).toBe("\nlater")
  	// reasoning_content should be preserved from the second message
  	__testAugmentVitest_1a4ccbe83779.expect(a.reasoning_content).toBe("keep-thoughts")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
