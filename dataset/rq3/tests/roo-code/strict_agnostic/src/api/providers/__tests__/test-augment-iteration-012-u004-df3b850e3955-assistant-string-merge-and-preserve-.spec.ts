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







  __testAugmentVitest_1a4ccbe83779.it("assistant_string_merge_and_preserve_reasoning_round_012", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// Two assistant messages with simple string content; second provides reasoning_content at top-level
  	const messages = [
  		{ role: "assistant", content: "a1" },
  		{ role: "assistant", content: "a2", reasoning_content: "r1" },
  	]

  	const result = convertToZAiFormat(messages, {})

  	// Should merge into a single assistant message and preserve reasoning_content from the second
  	__testAugmentVitest_1a4ccbe83779.expect(result.length).toBe(1)
  	const merged: any = result[0]
  	__testAugmentVitest_1a4ccbe83779.expect(merged.role).toBe("assistant")
  	__testAugmentVitest_1a4ccbe83779.expect(merged.content).toBe("a1\na2")
  	__testAugmentVitest_1a4ccbe83779.expect(merged.reasoning_content).toBe("r1")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
