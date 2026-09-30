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







  __testAugmentVitest_1a4ccbe83779.it("assistant_assign_content_when_prev_nonstring_and_preserve_reasoning_round_010_pass_02", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// First assistant has non-string content (null), second is a simple string with top-level reasoning_content
  	const messages: any[] = [
  		{ role: "assistant", content: null },
  		{ role: "assistant", content: "final-text", reasoning_content: "deep-thoughts" },
  	]

  	const out = convertToZAiFormat(messages)

  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	const am: any = out[0]
  	__testAugmentVitest_1a4ccbe83779.expect(am.role).toBe("assistant")
  	// Non-string previous content should be replaced by the new string
  	__testAugmentVitest_1a4ccbe83779.expect(am.content).toBe("final-text")
  	// reasoning_content from the second message should be preserved on the merged assistant message
  	__testAugmentVitest_1a4ccbe83779.expect(am.reasoning_content).toBe("deep-thoughts")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
