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








  __testAugmentVitest_a6a96b7a36c6.it("build_request_body_mcp_uses_additional_properties_false_only_round_003_pass_02", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const mockOptions: any = { apiModelId: "gpt-5.2-2025-12-11" }
  	const handler = new OpenAiCodexHandler(mockOptions)

  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("tok-mcp")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue(undefined)

  	// Force isMcpTool to return true for this test via dynamic import and spy.
  	const mcpModule = await import("../../../utils/mcp-name")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(mcpModule, "isMcpTool").mockReturnValue(true)

  	let capturedRequestBody: any = undefined
  	;(handler as any).client = {
  		responses: {
  			create: __testAugmentVitest_a6a96b7a36c6.vi.fn().mockImplementation(async (req: any) => {
  				capturedRequestBody = req
  				return {
  					async *[Symbol.asyncIterator]() {
  						yield { type: "response.completed", response: { id: "ok-mcp", output: [], usage: {} } }
  					},
  				}
  			}),
  		},
  	}

  	// Provide a tool; since isMcpTool is forced true, ensureAdditionalPropertiesFalse should be used
  	const metadata: any = {
  		tools: [
  			{
  				type: "function",
  				function: {
  					name: "mcp_tool_example",
  					parameters: { type: "object", properties: { a: { type: "string" }, b: { type: "number" } } },
  					description: "MCP tool",
  				},
  			},
  		],
  	}

  	for await (const _ of handler.createMessage("sys", [{ role: "user", content: "y" } as any], metadata)) {
  		// drain
  	}

  	__testAugmentVitest_a6a96b7a36c6.expect(capturedRequestBody).toBeDefined()
  	const params = capturedRequestBody.tools[0].parameters
  	__testAugmentVitest_a6a96b7a36c6.expect(params).toBeDefined()
  	// For MCP path additionalProperties must be false and properties preserved but required may not be set to all keys
  	__testAugmentVitest_a6a96b7a36c6.expect(params.additionalProperties).toBe(false)
  	// ensure that properties still include 'a' and 'b'
  	__testAugmentVitest_a6a96b7a36c6.expect(typeof params.properties.a).toBe("object")
  	__testAugmentVitest_a6a96b7a36c6.expect(typeof params.properties.b).toBe("object")
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
