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










  __testAugmentVitest_4d5df3bbaec0.it("remove_cache_points_and_supports_prompt_cache_round_018_pass_02", () => {
  	// removeCachePoints should strip cachePoint properties from array entries
  	const input = [
  		{ text: "a", cachePoint: { type: "default" }, other: 1 },
  		{ text: "b" },
  	]
  	const cleaned = (handler as any).removeCachePoints(input)
  	__testAugmentVitest_4d5df3bbaec0.expect(Array.isArray(cleaned)).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect(cleaned[0].cachePoint).toBeUndefined()
  	__testAugmentVitest_4d5df3bbaec0.expect(cleaned[0].other).toBe(1)

  	// Non-array should be returned unchanged
  	const primitive = "no-change"
  	__testAugmentVitest_4d5df3bbaec0.expect((handler as any).removeCachePoints(primitive)).toBe(primitive)

  	// supportsAwsPromptCache should be true only when supportsPromptCache and cachableFields exist
  	const okModel = { info: { supportsPromptCache: true, cachableFields: ["x"] } }
  	const notOkModel1 = { info: { supportsPromptCache: false, cachableFields: ["x"] } }
  	const notOkModel2 = { info: { supportsPromptCache: true, cachableFields: [] } }

  	__testAugmentVitest_4d5df3bbaec0.expect((handler as any).supportsAwsPromptCache(okModel)).toBe(true)
  	__testAugmentVitest_4d5df3bbaec0.expect((handler as any).supportsAwsPromptCache(notOkModel1)).toBe(false)
  	__testAugmentVitest_4d5df3bbaec0.expect((handler as any).supportsAwsPromptCache(notOkModel2)).toBe(false)
  })
})

import * as __testAugmentVitest_4d5df3bbaec0 from "vitest";

const __testAugmentLoadTarget_e836910265e8 = async () => {
  __testAugmentVitest_4d5df3bbaec0.vi.doUnmock("../bedrock.js");
  __testAugmentVitest_4d5df3bbaec0.vi.resetModules();
  return import("../bedrock.js");
};
