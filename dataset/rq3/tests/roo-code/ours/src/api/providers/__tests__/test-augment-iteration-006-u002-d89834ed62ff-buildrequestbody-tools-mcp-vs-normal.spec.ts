// npx vitest run api/providers/__tests__/openai-native.spec.ts

import { Anthropic } from "@anthropic-ai/sdk"
import OpenAI from "openai"

import {} from "@roo-code/types"

import { OpenAiNativeHandler } from "../openai-native"
import { ApiHandlerOptions } from "../../../shared/api"

// Mock OpenAI client - now everything uses Responses API
const mockResponsesCreate = vitest.fn()

vitest.mock("openai", () => {
	return {
		__esModule: true,
		default: vitest.fn().mockImplementation(() => ({
			responses: {
				create: mockResponsesCreate,
			},
		})),
	}
})

describe("OpenAiNativeHandler", () => {
	let handler: OpenAiNativeHandler
	let mockOptions: ApiHandlerOptions
	const systemPrompt = "You are a helpful assistant."
	const messages: Anthropic.Messages.MessageParam[] = [
		{
			role: "user",
			content: "Hello!",
		},
	]

	beforeEach(() => {
		mockOptions = {
			apiModelId: "gpt-4.1",
			openAiNativeApiKey: "test-api-key",
		}
		handler = new OpenAiNativeHandler(mockOptions)
		mockResponsesCreate.mockClear()
		// Clear fetch mock if it exists
		if ((global as any).fetch) {
			delete (global as any).fetch
		}
	})

	afterEach(() => {
		// Clean up fetch mock
		if ((global as any).fetch) {
			delete (global as any).fetch
		}
	})





  __testAugmentVitest_457083e09373.it("buildRequestBody tools MCP vs normal parameters_round_006", () => {
  	const model = handler.getModel()

  	// Normal tool: strict should be true and ensureAllRequired will add required array and additionalProperties:false
  	const normalTool = {
  		type: "function",
  		function: {
  			name: "normal-tool",
  			description: "normal",
  			parameters: {
  				type: "object",
  				properties: { a: { type: "string" } },
  				additionalProperties: true,
  			},
  		},
  	}

  	// MCP tool: name uses the MCP prefix; ensureAdditionalPropertiesFalse should be applied and strict:false
  	const mcpTool = {
  		type: "function",
  		function: {
  			name: "mcp--tool",
  			description: "mcp",
  			parameters: {
  				type: "object",
  				properties: {
  					b: {
  						type: "object",
  						properties: { x: { type: "string" } },
  					},
  				},
  			},
  		},
  	}

  	const metadata = { tools: [normalTool, mcpTool], tool_choice: undefined, parallelToolCalls: true }

  	const body = (handler as any).buildRequestBody(model, [], "system prompt", undefined, undefined, metadata)

  	__testAugmentVitest_457083e09373.expect(Array.isArray(body.tools)).toBe(true)
  	const t0 = body.tools[0]
  	const t1 = body.tools[1]

  	__testAugmentVitest_457083e09373.expect(t0.name).toBe("normal-tool")
  	// Normal tool should be strict=true and have required array and additionalProperties set to false by ensureAllRequired
  	__testAugmentVitest_457083e09373.expect(t0.strict).toBe(true)
  	__testAugmentVitest_457083e09373.expect(t0.parameters).toBeDefined()
  	__testAugmentVitest_457083e09373.expect(t0.parameters.additionalProperties).toBe(false)
  	__testAugmentVitest_457083e09373.expect(Array.isArray(t0.parameters.required)).toBe(true)

  	__testAugmentVitest_457083e09373.expect(t1.name).toBe("mcp--tool")
  	// MCP tool should be strict=false and still have additionalProperties:false (ensureAdditionalPropertiesFalse)
  	__testAugmentVitest_457083e09373.expect(t1.strict).toBe(false)
  	__testAugmentVitest_457083e09373.expect(t1.parameters.additionalProperties).toBe(false)
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
