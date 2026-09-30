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








  __testAugmentVitest_a6a96b7a36c6.it("refusal_delta_yields_text_round_003", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const mockOptions: any = { apiModelId: "gpt-5.2-2025-12-11" }
  	const handler = new OpenAiCodexHandler(mockOptions)

  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("tok-ref")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct-ref")

  	;(handler as any).client = {
  		responses: {
  			create: __testAugmentVitest_a6a96b7a36c6.vi.fn().mockResolvedValue({
  				async *[Symbol.asyncIterator]() {
  					yield { type: "response.refusal.delta", delta: "I refuse to comply" }
  					yield { type: "response.completed", response: { id: "r-ref-1", output: [], usage: {} } }
  				},
  			}),
  		},
  	}

  	const out: any[] = []
  	for await (const chunk of handler.createMessage("system", [{ role: "user", content: "please do forbidden" } as any], { taskId: "t-ref", tools: [] })) {
  		out.push(chunk)
  	}

  	const text = out.filter((c) => c.type === "text").map((c) => c.text).join("")
  	__testAugmentVitest_a6a96b7a36c6.expect(text).toContain("[Refusal] I refuse to comply")
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
