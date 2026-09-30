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










  __testAugmentVitest_4d5df3bbaec0.it("stream_metadata_and_prompt_router_usage_round_018", async () => {
  	// Stream should yield usage chunks when metadata.usage is present and when trace.promptRouter.usage is present
  	const metaEvent = {
  		metadata: {
  			usage: {
  				inputTokens: 10,
  				outputTokens: 20,
  				// use token-count variant for cache read
  				cacheReadInputTokenCount: 5,
  				cacheWriteInputTokens: 2,
  			},
  		},
  	}

  	const routerEvent = {
  		trace: {
  			promptRouter: {
  				invokedModelId: "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2",
  				usage: {
  					inputTokens: 3,
  					outputTokens: 4,
  					cacheReadTokens: 1,
  				},
  			},
  		},
  	}

  	const stream = {
  		[Symbol.asyncIterator]: async function* () {
  			yield JSON.stringify(metaEvent)
  			yield JSON.stringify(routerEvent)
  		},
  	}

  	mockSend.mockResolvedValueOnce({ stream })

  	const collected: any[] = []
  	for await (const chunk of handler.createMessage("system", [{ role: "user", content: "hi" }])) {
  		collected.push(chunk)
  	}

  	// Expect at least two usage chunks: one from metadata, one from promptRouter.usage
  	const usageChunks = collected.filter((c) => c.type === "usage")
  	__testAugmentVitest_4d5df3bbaec0.expect(usageChunks.length).toBeGreaterThanOrEqual(2)

  	// Validate first metadata usage has cacheReadTokens computed from cacheReadInputTokenCount
  	const metaUsage = usageChunks.find((u) => u.inputTokens === 10)
  	__testAugmentVitest_4d5df3bbaec0.expect(metaUsage).toBeDefined()
  	__testAugmentVitest_4d5df3bbaec0.expect(metaUsage.cacheReadTokens).toBe(5)

  	// Validate promptRouter usage is forwarded as usage chunk with the router values
  	const routerUsage = usageChunks.find((u) => u.inputTokens === 3)
  	__testAugmentVitest_4d5df3bbaec0.expect(routerUsage).toBeDefined()
  	__testAugmentVitest_4d5df3bbaec0.expect(routerUsage.cacheReadTokens).toBe(1)
  })
})

import * as __testAugmentVitest_4d5df3bbaec0 from "vitest";

const __testAugmentLoadTarget_e836910265e8 = async () => {
  __testAugmentVitest_4d5df3bbaec0.vi.doUnmock("../bedrock.js");
  __testAugmentVitest_4d5df3bbaec0.vi.resetModules();
  return import("../bedrock.js");
};
