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








  __testAugmentVitest_a6a96b7a36c6.it("handle_stream_response_parses_plain_json_lines_round_003_pass_03", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const handler = new OpenAiCodexHandler({ apiModelId: "gpt-5.2-2025-12-11" })
  	const model = handler.getModel()

  	// Build a fake ReadableStream-like body with a reader that yields a JSON line (no 'data: ' prefix)
  	const encoder = new TextEncoder()
  	let reads = 0
  	const reader = {
  		read: async () => {
  			reads++
  			if (reads === 1) {
  				return { done: false, value: encoder.encode(JSON.stringify({ content: "plain-hello" }) + "\n") }
  			}
  			return { done: true, value: undefined }
  		},
  		releaseLock: () => {},
  	}
  	const body = { getReader: () => reader }

  	const out: any[] = []
  	for await (const chunk of (handler as any).handleStreamResponse(body as any, model)) {
  		out.push(chunk)
  	}

  	const textChunks = out.filter((c) => c.type === "text").map((c) => c.text)
  	__testAugmentVitest_a6a96b7a36c6.expect(textChunks.join("")).toContain("plain-hello")
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
