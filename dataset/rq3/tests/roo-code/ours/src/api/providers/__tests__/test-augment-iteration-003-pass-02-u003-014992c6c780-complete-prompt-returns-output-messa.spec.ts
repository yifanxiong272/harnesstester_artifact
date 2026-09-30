// cd src && npx vitest run api/providers/__tests__/openai-codex-native-tool-calls.spec.ts

import { beforeEach, describe, expect, it, vi } from "vitest"

import { OpenAiCodexHandler } from "../openai-codex"
import type { ApiHandlerOptions } from "../../../shared/api"
import { NativeToolCallParser } from "../../../core/assistant-message/NativeToolCallParser"
import { openAiCodexOAuthManager } from "../../../integrations/openai-codex/oauth"

describe("OpenAiCodexHandler native tool calls", () => {
	let handler: OpenAiCodexHandler
	let mockOptions: ApiHandlerOptions

	beforeEach(() => {
		vi.restoreAllMocks()
		NativeToolCallParser.clearRawChunkState()
		NativeToolCallParser.clearAllStreamingToolCalls()

		mockOptions = {
			apiModelId: "gpt-5.2-2025-12-11",
			// minimal settings; OAuth is mocked below
		}
		handler = new OpenAiCodexHandler(mockOptions)
	})








  __testAugmentVitest_a6a96b7a36c6.it("complete_prompt_returns_output_message_text_round_003_pass_02", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const handler = new OpenAiCodexHandler({ apiModelId: "gpt-5.2-2025-12-11" })

  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("tok-complete")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue(undefined)

  	// Mock fetch for the non-streaming completePrompt path
  	const fakeResponseData = {
  		output: [
  			{ type: "message", content: [{ type: "output_text", text: "final-text-from-server" }] },
  		],
  	}

  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(globalThis as any, "fetch").mockResolvedValue({
  		ok: true,
  		json: async () => fakeResponseData,
  		text: async () => JSON.stringify(fakeResponseData),
  	})

  	const result = await handler.completePrompt("prompt here")
  	__testAugmentVitest_a6a96b7a36c6.expect(result).toBe("final-text-from-server")
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
