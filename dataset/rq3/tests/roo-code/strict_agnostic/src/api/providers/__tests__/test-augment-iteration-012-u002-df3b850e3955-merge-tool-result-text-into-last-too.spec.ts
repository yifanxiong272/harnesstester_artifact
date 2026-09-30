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







  __testAugmentVitest_1a4ccbe83779.it("merge_tool_result_text_into_last_tool_message_round_012", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	// A user message containing a tool_result followed by a text part.
  	const messages = [
  		{
  			role: "user",
  			content: [
  				{ type: "tool_result", tool_use_id: "t1", content: "tool-output" },
  				{ type: "text", text: "extra text" },
  			],
  		},
  	]

  	const result = convertToZAiFormat(messages, { mergeToolResultText: true })

  	// The tool result should be emitted as a tool message and the trailing text merged into it
  	__testAugmentVitest_1a4ccbe83779.expect(result.length).toBe(1)
  	const toolMsg: any = result[0]
  	__testAugmentVitest_1a4ccbe83779.expect(toolMsg.role).toBe("tool")
  	__testAugmentVitest_1a4ccbe83779.expect(toolMsg.tool_call_id).toBe("t1")
  	// Merged content should include original tool output, two newlines, then the extra text
  	__testAugmentVitest_1a4ccbe83779.expect(toolMsg.content).toBe("tool-output\n\nextra text")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
