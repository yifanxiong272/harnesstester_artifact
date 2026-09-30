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










  __testAugmentVitest_4d5df3bbaec0.it("guess_model_info_from_id_round_018", () => {
  	// getModelById should fall back to guessModelInfoFromId for unknown IDs and pick up 'claude-4' heuristics
  	const guessed = handler.getModelById("my-custom-claude-4-extra")
  	// The heuristic for claude-4 sets maxTokens to 8192 and supportsImages true
  	__testAugmentVitest_4d5df3bbaec0.expect(guessed.info.maxTokens).toBe(8192)
  	__testAugmentVitest_4d5df3bbaec0.expect(guessed.info.supportsImages).toBe(true)
  })
})

import * as __testAugmentVitest_4d5df3bbaec0 from "vitest";

const __testAugmentLoadTarget_e836910265e8 = async () => {
  __testAugmentVitest_4d5df3bbaec0.vi.doUnmock("../bedrock.js");
  __testAugmentVitest_4d5df3bbaec0.vi.resetModules();
  return import("../bedrock.js");
};
