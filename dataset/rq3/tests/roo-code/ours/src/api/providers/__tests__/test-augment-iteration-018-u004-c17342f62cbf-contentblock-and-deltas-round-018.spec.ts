const mockCaptureException = vi.hoisted(() => vi.fn())

// Mock BedrockRuntimeClient and commands
const mockSend = vi.fn()

// Mock AWS SDK credential providers
vi.mock("@aws-sdk/credential-providers", () => {
	return {
		fromIni: vi.fn().mockReturnValue({
			accessKeyId: "profile-access-key",
			secretAccessKey: "profile-secret-key",
		}),
	}
})

vi.mock("@aws-sdk/client-bedrock-runtime", () => ({
	BedrockRuntimeClient: vi.fn().mockImplementation(() => ({
		send: mockSend,
	})),
	ConverseStreamCommand: vi.fn(),
	ConverseCommand: vi.fn(),
}))

import { AwsBedrockHandler } from "../bedrock"
import { Anthropic } from "@anthropic-ai/sdk"

describe("AwsBedrockHandler Error Handling", () => {
	let handler: AwsBedrockHandler

	beforeEach(() => {
		vi.clearAllMocks()
		mockCaptureException.mockClear()
		handler = new AwsBedrockHandler({
			apiModelId: "anthropic.claude-3-5-sonnet-20241022-v2:0",
			awsAccessKey: "test-access-key",
			awsSecretKey: "test-secret-key",
			awsRegion: "us-east-1",
		})
	})

	const createMockError = (options: {
		message?: string
		name?: string
		status?: number
		__type?: string
		$metadata?: {
			httpStatusCode?: number
			requestId?: string
			extendedRequestId?: string
			cfId?: string
			[key: string]: any // Allow additional properties
		}
	}): Error => {
		const error = new Error(options.message || "Test error") as any
		if (options.name) error.name = options.name
		if (options.status) error.status = options.status
		if (options.__type) error.__type = options.__type
		if (options.$metadata) error.$metadata = options.$metadata
		return error
	}










  __testAugmentVitest_4d5df3bbaec0.it("contentblock_and_deltas_round_018", async () => {
  	// Build a stream that contains a variety of contentBlockStart and contentBlockDelta shapes
  	const events = []

  	// contentBlockStart -> reasoningContent with contentBlockIndex > 0 should yield a newline chunk then reasoning text
  	events.push({ contentBlockStart: { contentBlock: { reasoningContent: { text: "reasoning text" } }, contentBlockIndex: 1 } })

  	// contentBlockStart -> alternative thinking structure content_block.type === 'thinking'
  	events.push({ contentBlockStart: { content_block: { type: "thinking", thinking: "thinking-text" }, contentBlockIndex: 0 } })

  	// contentBlockStart -> tool use start
  	events.push({ contentBlockStart: { start: { toolUse: { toolUseId: "tu-1", name: "tool-name" } }, contentBlockIndex: 2 } })

  	// contentBlockStart -> start.text
  	events.push({ contentBlockStart: { start: { text: "plain text" } } })

  	// contentBlockDelta -> reasoningContent
  	events.push({ contentBlockDelta: { delta: { reasoningContent: { text: "delta reasoning" } } } })

  	// contentBlockDelta -> toolUse.input
  	events.push({ contentBlockDelta: { contentBlockIndex: 5, delta: { toolUse: { input: '{"arg":"value"}' } } } })

  	// contentBlockDelta -> thinking_delta structure
  	events.push({ contentBlockDelta: { delta: { type: "thinking_delta", thinking: "delta thinking" } } })

  	// contentBlockDelta -> text
  	events.push({ contentBlockDelta: { delta: { text: "delta text" } } })

  	const stream = {
  		[Symbol.asyncIterator]: async function* () {
  			for (const e of events) {
  				yield JSON.stringify(e)
  			}
  		},
  	}

  	mockSend.mockResolvedValueOnce({ stream })

  	const chunks: any[] = []
  	for await (const c of handler.createMessage("system", [{ role: "user", content: "hello" }])) {
  		chunks.push(c)
  	}

  	// Assertions cover each branch outcome
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "reasoning" && typeof c.text === "string" && c.text.includes("reasoning text"))).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "reasoning" && c.text === "thinking-text")).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "tool_call_partial" && c.id === "tu-1" && c.name === "tool-name")).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "text" && c.text === "plain text")).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "reasoning" && c.text === "delta reasoning")).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "tool_call_partial" && c.arguments && c.arguments.includes('"arg":"value"'))).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "reasoning" && c.text === "delta thinking")).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(chunks.some((c) => c.type === "text" && c.text === "delta text")).toBe(true)
  })
})

import * as __testAugmentVitest_4d5df3bbaec0 from "vitest";

const __testAugmentLoadTarget_e836910265e8 = async () => {
  __testAugmentVitest_4d5df3bbaec0.vi.doUnmock("../bedrock.js");
  __testAugmentVitest_4d5df3bbaec0.vi.resetModules();
  return import("../bedrock.js");
};
