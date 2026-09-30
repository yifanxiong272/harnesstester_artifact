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






	  __testAugmentVitest_b30b0a453b49.it("objectToUrlEncoded_body_round_021_pass_02", async () => {
	  	__testAugmentVitest_b30b0a453b49.vi.clearAllMocks()

	  	// Prepare a handler instance; we will invoke doRefreshAccessToken directly to observe the fetch body
	  	const { QwenCodeHandler } = __testAugmentTarget_d1870a305c9a
	  	const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus", qwenCodeOauthPath: "./token.json" })

	  	const creds = { access_token: "old", refresh_token: "r_tok", token_type: "Bearer", expiry_date: Date.now() - 10000 }

	  	// Capture fetch arguments and return a successful token response
	  	const originalFetch = (globalThis as any).fetch
	  	let captured: any = {}
	  	;(globalThis as any).fetch = async (url: any, opts: any) => {
	  		captured.url = url
	  		captured.opts = opts
	  		return {
	  			ok: true,
	  			json: async () => ({ access_token: "new_access", token_type: "Bearer", expires_in: 3600, refresh_token: "maybe_new" }),
	  		}
	  	}

	  	try {
	  		const newCreds = await (handler as any).doRefreshAccessToken(creds)
	  		__testAugmentVitest_b30b0a453b49.expect(newCreds.access_token).toBe("new_access")
	  		// Ensure fetch was called and that the body contains the expected urlencoded pieces
	  		__testAugmentVitest_b30b0a453b49.expect(captured.opts).toBeDefined()
	  		__testAugmentVitest_b30b0a453b49.expect(captured.opts.method).toBe("POST")
	  		__testAugmentVitest_b30b0a453b49.expect(captured.opts.headers["Content-Type"]).toBe("application/x-www-form-urlencoded")
	  		__testAugmentVitest_b30b0a453b49.expect(typeof captured.opts.body).toBe("string")
	  		// Should contain grant_type=refresh_token and the refresh token and client_id
	  		__testAugmentVitest_b30b0a453b49.expect(captured.opts.body.includes("grant_type=refresh_token")).toBe(true)
	  		__testAugmentVitest_b30b0a453b49.expect(captured.opts.body.includes(encodeURIComponent("r_tok"))).toBe(true)
	  		__testAugmentVitest_b30b0a453b49.expect(captured.opts.body.includes("client_id=")).toBe(true)
	  	} finally {
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
