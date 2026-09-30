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








  __testAugmentVitest_a6a96b7a36c6.it("completePrompt_fetch_error_wrapped_assertion_round_003_pass_02", async () => {
  	// Arrange: ensure OAuth provides a token (even if it will be rejected by backend) and no account id
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("bad-token")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue(undefined)

  	// Stub fetch to return a non-ok response with a JSON error body
  	__testAugmentVitest_a6a96b7a36c6.vi.stubGlobal("fetch", () =>
  		Promise.resolve({
  			ok: false,
  			status: 400,
  			text: async () => JSON.stringify({ error: { message: "invalid prompt" } }),
  		}),
  	)

  	let caught: any = null
  	try {
  		await handler.completePrompt("test prompt")
  	} catch (e: any) {
  		caught = e
  	}

  	// Assert: an error was thrown and its message is the wrapped i18n text (translation key/label)
  	__testAugmentVitest_a6a96b7a36c6.expect(caught).toBeInstanceOf(Error)
  	__testAugmentVitest_a6a96b7a36c6.expect(String(caught.message)).toContain("openAiCodex.completionError")

  	// Also ensure the handler cleaned up its abortController in the finally block
  	__testAugmentVitest_a6a96b7a36c6.expect((handler as any).abortController).toBeUndefined()
  });
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
