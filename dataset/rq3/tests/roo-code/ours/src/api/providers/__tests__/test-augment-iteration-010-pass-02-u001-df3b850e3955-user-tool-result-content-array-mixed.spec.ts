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







  __testAugmentVitest_1a4ccbe83779.it("user_tool_result_content_array_mixed_round_010_pass_02", async () => {
  	const { convertToZAiFormat } = await __testAugmentLoadTarget_e3e56a09bbd7()

  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{
  					type: "tool_result",
  					tool_use_id: "tr-1",
  					content: [
  						{ type: "text", text: "part-text" },
  						{ type: "image" },
  						{ type: "unknown" },
  					],
  				},
  			],
  		},
  	]

  	const out = convertToZAiFormat(messages)

  	__testAugmentVitest_1a4ccbe83779.expect(out.length).toBe(1)
  	const tool = out[0]
  	__testAugmentVitest_1a4ccbe83779.expect(tool.role).toBe("tool")
  	__testAugmentVitest_1a4ccbe83779.expect(tool.tool_call_id).toBe("tr-1")
  	// Mapped text and (image); unknown type becomes an empty string element in the join
  	__testAugmentVitest_1a4ccbe83779.expect(tool.content).toBe("part-text\n(image)\n")
  })
})

import * as __testAugmentVitest_1a4ccbe83779 from "vitest";

const __testAugmentLoadTarget_e3e56a09bbd7 = async () => {
  __testAugmentVitest_1a4ccbe83779.vi.doUnmock("../../transform/zai-format.js");
  __testAugmentVitest_1a4ccbe83779.vi.resetModules();
  return import("../../transform/zai-format.js");
};
