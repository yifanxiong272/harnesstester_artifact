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








  __testAugmentVitest_a6a96b7a36c6.it("build_request_body_ensures_all_required_for_non_mcp_round_003_pass_02", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const mockOptions: any = { apiModelId: "gpt-5.2-2025-12-11" }
  	const handler = new OpenAiCodexHandler(mockOptions)

  	// OAuth mocked so handler proceeds
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("tok-tools")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue(undefined)

  	let capturedRequestBody: any = undefined

  	// Inject a fake SDK client; capture the requestBody passed to create()
  	;(handler as any).client = {
  		responses: {
  			create: __testAugmentVitest_a6a96b7a36c6.vi.fn().mockImplementation(async (req: any) => {
  				capturedRequestBody = req
  				return {
  					async *[Symbol.asyncIterator]() {
  						yield { type: "response.completed", response: { id: "ok", output: [], usage: {} } }
  					},
  				}
  			}),
  		},
  	}

  	// Provide metadata.tools with a function tool that has nested parameter objects/arrays
  	const metadata: any = {
  		tools: [
  			{
  				type: "function",
  				function: {
  					name: "normal_tool",
  					description: "A normal function",
  					parameters: {
  						type: "object",
  						properties: {
  							alpha: { type: "string" },
  							nested: { type: "object", properties: { x: { type: "number" }, y: { type: "string" } } },
  							arr: { type: "array", items: { type: "object", properties: { v: { type: "string" } } } },
  						},
  					},
  				},
  			},
  		],
  	}

  	// Call createMessage so buildRequestBody runs and we capture requestBody
  	for await (const _ of handler.createMessage("sys", [{ role: "user", content: "x" } as any], metadata)) {
  		// drain
  	}

  	__testAugmentVitest_a6a96b7a36c6.expect(capturedRequestBody).toBeDefined()
  	// tools array should have been created and first tool.parameters should have additionalProperties false (ensureAllRequired)
  	__testAugmentVitest_a6a96b7a36c6.expect(Array.isArray(capturedRequestBody.tools)).toBe(true)
  	const toolParams = capturedRequestBody.tools[0].parameters
  	__testAugmentVitest_a6a96b7a36c6.expect(toolParams).toBeDefined()
  	__testAugmentVitest_a6a96b7a36c6.expect(toolParams.additionalProperties).toBe(false)
  	// required should include keys alpha, nested, arr
  	__testAugmentVitest_a6a96b7a36c6.expect(Array.isArray(toolParams.required)).toBe(true)
  	__testAugmentVitest_a6a96b7a36c6.expect(toolParams.required).toEqual(__testAugmentVitest_a6a96b7a36c6.expect.arrayContaining(["alpha", "nested", "arr"]))
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
