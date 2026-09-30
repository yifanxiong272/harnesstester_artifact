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










  __testAugmentVitest_4d5df3bbaec0.it("convert_tool_choice_variants_round_018_pass_02", () => {
  	// Access private converter via any to exercise all branches for tool_choice conversion
  	const convert = (handler as any).convertToolChoiceForBedrock.bind(handler)

  	// Undefined -> default auto
  	const undefinedChoice = convert(undefined)
  	__testAugmentVitest_4d5df3bbaec0.expect(undefinedChoice).toBeDefined()
  	__testAugmentVitest_4d5df3bbaec0.expect(undefinedChoice).toHaveProperty("auto")

  	// String 'none' -> should return undefined (omit tools)
  	const noneChoice = convert("none")
  	__testAugmentVitest_4d5df3bbaec0.expect(noneChoice).toBeUndefined()

  	// String 'required' -> returns { any: {} }
  	const requiredChoice = convert("required")
  	__testAugmentVitest_4d5df3bbaec0.expect(requiredChoice).toBeDefined()
  	__testAugmentVitest_4d5df3bbaec0.expect(requiredChoice).toHaveProperty("any")

  	// Object form with function -> returns specific tool name mapping
  	const objectChoice = convert({ function: { name: "myTool" } })
  	__testAugmentVitest_4d5df3bbaec0.expect(objectChoice).toBeDefined()
  	__testAugmentVitest_4d5df3bbaec0.expect(objectChoice.tool).toBeDefined()
  	__testAugmentVitest_4d5df3bbaec0.expect(objectChoice.tool.name).toBe("myTool")
  })
})

import * as __testAugmentVitest_4d5df3bbaec0 from "vitest";

const __testAugmentLoadTarget_e836910265e8 = async () => {
  __testAugmentVitest_4d5df3bbaec0.vi.doUnmock("../bedrock.js");
  __testAugmentVitest_4d5df3bbaec0.vi.resetModules();
  return import("../bedrock.js");
};
