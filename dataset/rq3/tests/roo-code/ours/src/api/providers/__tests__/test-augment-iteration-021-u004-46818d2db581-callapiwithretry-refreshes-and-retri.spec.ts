// npx vitest run api/providers/__tests__/qwen-code-native-tools.spec.ts

// Mock filesystem - must come before other imports
vi.mock("node:fs", () => ({
	promises: {
		readFile: vi.fn(),
		writeFile: vi.fn(),
	},
}))

const mockCreate = vi.fn()
vi.mock("openai", () => {
	return {
		__esModule: true,
		default: vi.fn().mockImplementation(() => ({
			apiKey: "test-key",
			baseURL: "https://dashscope.aliyuncs.com/compatible-mode/v1",
			chat: {
				completions: {
					create: mockCreate,
				},
			},
		})),
	}
})

import { promises as fs } from "node:fs"
import { QwenCodeHandler } from "../qwen-code"
import { NativeToolCallParser } from "../../../core/assistant-message/NativeToolCallParser"
import type { ApiHandlerOptions } from "../../../shared/api"

describe("QwenCodeHandler Native Tools", () => {
	let handler: QwenCodeHandler
	let mockOptions: ApiHandlerOptions & { qwenCodeOauthPath?: string }

	const testTools = [
		{
			type: "function" as const,
			function: {
				name: "test_tool",
				description: "A test tool",
				parameters: {
					type: "object",
					properties: {
						arg1: { type: "string", description: "First argument" },
					},
					required: ["arg1"],
				},
			},
		},
	]

	beforeEach(() => {
		vi.clearAllMocks()

		// Mock credentials file
		const mockCredentials = {
			access_token: "test-access-token",
			refresh_token: "test-refresh-token",
			token_type: "Bearer",
			expiry_date: Date.now() + 3600000, // 1 hour from now
			resource_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
		}
		;(fs.readFile as any).mockResolvedValue(JSON.stringify(mockCredentials))
		;(fs.writeFile as any).mockResolvedValue(undefined)

		mockOptions = {
			apiModelId: "qwen3-coder-plus",
		}
		handler = new QwenCodeHandler(mockOptions)

		// Clear NativeToolCallParser state before each test
		NativeToolCallParser.clearRawChunkState()
	})

	describe("Native Tool Calling Support", () => {






	  __testAugmentVitest_b30b0a453b49.it("callApiWithRetry_refreshes_and_retries_round_021", async () => {
	  	__testAugmentVitest_b30b0a453b49.vi.clearAllMocks()

	  	// Initial credentials (valid but we will simulate an API 401 to force refresh flow)
	  	const initialCreds = {
	  		access_token: "initial-token",
	  		refresh_token: "refresh-me",
	  		token_type: "Bearer",
	  		expiry_date: Date.now() + 1000_000,
	  		resource_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
	  	}
	  	;(fs.readFile as any).mockResolvedValue(JSON.stringify(initialCreds))

	  	const { QwenCodeHandler } = __testAugmentTarget_d1870a305c9a
	  	const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus" })

	  	// Ensure client exists so we can replace its create implementation
	  	await (handler as any).ensureAuthenticated()
	  	const client = (handler as any).client
	  	__testAugmentVitest_b30b0a453b49.expect(client).toBeDefined()

	  	// Make create throw a 401 first, then succeed on retry
	  	let callCount = 0
	  	client.chat.completions.create = async () => {
	  		callCount++
	  		if (callCount === 1) {
	  			const err: any = new Error("unauthorized")
	  			err.status = 401
	  			throw err
	  		}
	  		return { choices: [{ message: { content: "final-result" } }] }
	  	}

	  	// Replace the handler's refreshAccessToken to simulate obtaining a refreshed token
	  	;(handler as any).refreshAccessToken = async (oldCreds: any) => {
	  		const newCreds = {
	  			...oldCreds,
	  			access_token: "refreshed-token",
	  			expiry_date: Date.now() + 1000_000,
	  		}
	  		// Simulate in-memory update that the real refreshAccessToken would perform
	  		;(handler as any).credentials = newCreds
	  		return newCreds
	  	}

	  	// Now call completePrompt which uses callApiWithRetry internally and should retry after 401
	  	const result = await handler.completePrompt("some prompt")

	  	__testAugmentVitest_b30b0a453b49.expect(result).toBe("final-result")
	  	__testAugmentVitest_b30b0a453b49.expect(callCount).toBe(2)
	  	// Client apiKey should be updated to the refreshed token by the retry logic
	  	__testAugmentVitest_b30b0a453b49.expect((handler as any).client.apiKey).toBe("refreshed-token")
	  })
	})
})

import * as __testAugmentVitest_b30b0a453b49 from "vitest";

import * as __testAugmentTarget_d1870a305c9a from "../qwen-code.js";

const __testAugmentLoadTarget_d1870a305c9a = async () => {
  __testAugmentVitest_b30b0a453b49.vi.doUnmock("../qwen-code.js");
  __testAugmentVitest_b30b0a453b49.vi.resetModules();
  return import("../qwen-code.js");
};
