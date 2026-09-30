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






	  __testAugmentVitest_b30b0a453b49.it("think_tag_parsing_round_021_pass_02", async () => {
	  	__testAugmentVitest_b30b0a453b49.vi.clearAllMocks()

	  	// Provide valid cached creds so ensureAuthenticated succeeds
	  	;(fs.readFile as any).mockResolvedValue(JSON.stringify({ access_token: "tk", refresh_token: "rt", token_type: "Bearer", expiry_date: Date.now() + 3600000 }))

	  	// Arrange the OpenAI client to stream a single chunk containing a think block
	  	mockCreate.mockImplementationOnce(() => ({
	  		[Symbol.asyncIterator]: async function* () {
	  			yield { choices: [ { delta: { content: "Hello<think>INNER</think>World" } } ] }
	  		},
	  	}))

	  	const { QwenCodeHandler } = __testAugmentTarget_d1870a305c9a
	  	const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus" })

	  	const results: any[] = []
	  	for await (const chunk of handler.createMessage("sys", [], {} as any)) {
	  		results.push(chunk)
	  	}

	  	// Expect the content to be split into three events: text Hello, reasoning INNER, text World
	  	__testAugmentVitest_b30b0a453b49.expect(results.length).toBeGreaterThanOrEqual(3)
	  	// Find in-order occurrences
	  	__testAugmentVitest_b30b0a453b49.expect(results[0]).toEqual(expect.objectContaining({ type: "text", text: "Hello" }))
	  	__testAugmentVitest_b30b0a453b49.expect(results[1]).toEqual(expect.objectContaining({ type: "reasoning", text: "INNER" }))
	  	__testAugmentVitest_b30b0a453b49.expect(results[2]).toEqual(expect.objectContaining({ type: "text", text: "World" }))
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
