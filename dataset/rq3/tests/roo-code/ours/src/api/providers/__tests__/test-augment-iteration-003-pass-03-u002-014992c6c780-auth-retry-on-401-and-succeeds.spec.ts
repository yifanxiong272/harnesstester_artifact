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








  __testAugmentVitest_a6a96b7a36c6.it("auth_retry_on_401_and_succeeds_round_003_pass_03", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const handler = new OpenAiCodexHandler({ apiModelId: "gpt-5.2-2025-12-11" })

  	// Initial token present but executeRequest will throw an auth-like error first
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("old-token")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "forceRefreshAccessToken").mockResolvedValue("new-token")

  	let callCount = 0
  	// Replace the (private) executeRequest with an async generator that fails once then yields a text chunk
  	;(handler as any).executeRequest = async function* () {
  		callCount++
  		if (callCount === 1) {
  			throw new Error("401 unauthorized: token expired")
  		}
  		yield { type: "text", text: "after-refresh" }
  	}

  	const out: any[] = []
  	for await (const chunk of handler.createMessage("sys", [{ role: "user", content: "x" } as any], { taskId: "t", tools: [] })) {
  		out.push(chunk)
  	}

  	const texts = out.filter((c) => c.type === "text").map((c) => c.text)
  	__testAugmentVitest_a6a96b7a36c6.expect(texts.join("")).toContain("after-refresh")
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
