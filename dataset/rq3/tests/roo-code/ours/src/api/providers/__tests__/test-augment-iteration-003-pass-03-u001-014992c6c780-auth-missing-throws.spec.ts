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








  __testAugmentVitest_a6a96b7a36c6.it("auth_missing_throws_round_003_pass_03", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const handler = new OpenAiCodexHandler({ apiModelId: "gpt-5.2-2025-12-11" })

  	// Simulate not authenticated
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue(undefined)

  	const gen = handler.createMessage("sys", [{ role: "user", content: "x" } as any], {})
  	// The generator should reject because accessToken is missing
  	await __testAugmentVitest_a6a96b7a36c6.expect((gen as any).next()).rejects.toThrow(/Not authenticated/)
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
