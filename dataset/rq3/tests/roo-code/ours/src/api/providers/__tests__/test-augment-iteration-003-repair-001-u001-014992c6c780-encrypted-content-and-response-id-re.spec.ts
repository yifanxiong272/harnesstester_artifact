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








  __testAugmentVitest_a6a96b7a36c6.it("get_encrypted_content_and_response_id_round_003", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const mockOptions: any = { apiModelId: "gpt-5.2-2025-12-11" }
  	const handler = new OpenAiCodexHandler(mockOptions)

  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("tok-enc")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue(undefined)

  	// Inject preferred SDK streaming; emit a completed response containing a reasoning item with encrypted_content + id
  	;(handler as any).client = {
  		responses: {
  			create: __testAugmentVitest_a6a96b7a36c6.vi.fn().mockResolvedValue({
  				async *[Symbol.asyncIterator]() {
  					yield {
  						type: "response.completed",
  						response: {
  							id: "resp-enc-1",
  							output: [
  								{ type: "reasoning", encrypted_content: "ENC_PAYLOAD", id: "reason-42" },
  							],
  							usage: {},
  						},
  					}
  				},
  			}),
  		},
  	}

  	// Drain the stream so internal state (lastResponseOutput / lastResponseId) is populated
  	for await (const _ of handler.createMessage("system", [{ role: "user", content: "x" } as any], { taskId: "t-enc", tools: [] })) {
  		// noop - just iterate
  	}

  	const enc = handler.getEncryptedContent()
  	__testAugmentVitest_a6a96b7a36c6.expect(enc).toBeDefined()
  	__testAugmentVitest_a6a96b7a36c6.expect(enc?.encrypted_content).toBe("ENC_PAYLOAD")
  	__testAugmentVitest_a6a96b7a36c6.expect(enc?.id).toBe("reason-42")
  	// getResponseId should reflect the last response id observed
  	__testAugmentVitest_a6a96b7a36c6.expect(handler.getResponseId()).toBe("resp-enc-1")
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
