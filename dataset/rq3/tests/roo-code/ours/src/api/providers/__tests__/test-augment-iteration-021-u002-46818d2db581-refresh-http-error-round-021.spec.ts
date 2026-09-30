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






	  __testAugmentVitest_b30b0a453b49.it("refresh_http_error_round_021", async () => {
	  	__testAugmentVitest_b30b0a453b49.vi.clearAllMocks()

	  	// Credentials have refresh_token but are expired so refresh will be attempted
	  	const creds = {
	  		access_token: "old-access",
	  		refresh_token: "present-refresh",
	  		token_type: "Bearer",
	  		expiry_date: Date.now() - 5000,
	  	}
	  	;(fs.readFile as any).mockResolvedValue(JSON.stringify(creds))

	  	// Stub global.fetch to simulate an HTTP failure response from token endpoint
	  	const originalFetch = (globalThis as any).fetch
	  	;(globalThis as any).fetch = async () => ({
	  		ok: false,
	  		status: 400,
	  		statusText: "Bad Req",
	  		text: async () => "oops",
	  	} as any)

	  	try {
	  		const { QwenCodeHandler } = __testAugmentTarget_d1870a305c9a
	  		const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus" })

	  		// Expect the token refresh path to surface an HTTP error
	  		await __testAugmentVitest_b30b0a453b49.expect(handler.completePrompt("prompt")).rejects.toThrow(/Token refresh failed: 400 Bad Req/)
	  	} finally {
	  		// restore fetch to avoid affecting other tests
	  		;(globalThis as any).fetch = originalFetch
	  	}
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
