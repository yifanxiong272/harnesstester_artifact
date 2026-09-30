import { ContentBlock, SystemContentBlock, BedrockRuntimeClient } from "@aws-sdk/client-bedrock-runtime"
import { Anthropic } from "@anthropic-ai/sdk"

import { MultiPointStrategy } from "../multi-point-strategy"
import { CacheStrategyConfig, ModelInfo, CachePointPlacement } from "../types"
import { AwsBedrockHandler } from "../../../providers/bedrock"

// Common test utilities
const defaultModelInfo: ModelInfo = {
	maxTokens: 8192,
	contextWindow: 200_000,
	supportsPromptCache: true,
	maxCachePoints: 4,
	minTokensPerCachePoint: 50,
	cachableFields: ["system", "messages", "tools"],
}

const createConfig = (overrides: Partial<CacheStrategyConfig> = {}): CacheStrategyConfig => ({
	modelInfo: {
		...defaultModelInfo,
		...(overrides.modelInfo || {}),
	},
	systemPrompt: "You are a helpful assistant",
	messages: [],
	usePromptCache: true,
	...overrides,
})

const createMessageWithTokens = (role: "user" | "assistant", tokenCount: number) => ({
	role,
	content: "x".repeat(tokenCount * 4), // Approximate 4 chars per token
})

const hasCachePoint = (block: ContentBlock | SystemContentBlock): boolean => {
	return (
		"cachePoint" in block &&
		typeof block.cachePoint === "object" &&
		block.cachePoint !== null &&
		"type" in block.cachePoint &&
		block.cachePoint.type === "default"
	)
}

// Create a mock object to store the last config passed to convertToBedrockConverseMessages
interface CacheConfig {
	modelInfo: any
	systemPrompt?: string
	messages: any[]
	usePromptCache: boolean
}

const convertToBedrockConverseMessagesMock = {
	lastConfig: null as CacheConfig | null,
	result: null as any,
}

describe("Cache Strategy", () => {
	// SECTION 1: Direct Strategy Implementation Tests

	// SECTION 2: AwsBedrockHandler Integration Tests

	// SECTION 3: Multi-Point Strategy Cache Point Placement Tests
	describe("Multi-Point Strategy Cache Point Placement", () => {
		// These tests match the examples in the cache-strategy-documentation.md file

		// Common model info for all tests
		const multiPointModelInfo: ModelInfo = {
			maxTokens: 4096,
			contextWindow: 200000,
			supportsPromptCache: true,
			maxCachePoints: 3,
			minTokensPerCachePoint: 50, // Lower threshold to ensure tests pass
			cachableFields: ["system", "messages"],
		}

		// Helper function to create a message with approximate token count
		const createMessage = (role: "user" | "assistant", content: string, tokenCount: number) => {
			// Pad the content to reach the desired token count (approx 4 chars per token)
			const paddingNeeded = Math.max(0, tokenCount * 4 - content.length)
			const padding = " ".repeat(paddingNeeded)
			return {
				role,
				content: content + padding,
			}
		}

		// Helper to log cache point placements for debugging
		const logPlacements = (placements: any[]) => {
			console.log(
				"Cache point placements:",
				placements.map((p) => `index: ${p.index}, tokens: ${p.tokensCovered}`),
			)
		}





	  __testAugmentVitest_7816bcbcfc0c.it("combining_not_beneficial_keeps_existing_round_037_pass_02", async () => {
	  	const { MultiPointStrategy } = __testAugmentTarget_055ee19ba3f8
	  	const logging = await import("../../../../utils/logging")
	  	const infoSpy = __testAugmentVitest_7816bcbcfc0c.vi.spyOn(logging.logger, "info")

	  	// Patch estimateTokenCount so that tokensBetweenPlacements are large but new messages are small
	  	const originalEstimate = (MultiPointStrategy as any).prototype.estimateTokenCount
	  	;(MultiPointStrategy as any).prototype.estimateTokenCount = function (msg: any) {
	  		const text = typeof msg.content === 'string' ? msg.content : String(msg.content?.[0]?.text || '')
	  		// Mark older conversation messages as BIG to make tokensBetweenPlacements large
	  		if (text.includes('BIG')) return 100
	  		// New messages are small
	  		return 10
	  	}

	  	try {
	  		// messages: indices 0..4, previous placements at 1 and 3
	  		const messages = [
	  			{ role: "user", content: "BIG-0" },
	  			{ role: "assistant", content: "BIG-1" }, // previous placement 1 covers messages 0..1
	  			{ role: "user", content: "BIG-2" },
	  			{ role: "assistant", content: "BIG-3" }, // previous placement 3 covers messages 2..3
	  			{ role: "user", content: "small-new" }, // new messages start here with small tokens
	  		]

	  		const previousCachePointPlacements = [
	  			{ index: 1, type: "message", tokensCovered: 200 },
	  			{ index: 3, type: "message", tokensCovered: 200 },
	  		]

	  		// minTokensPerCachePoint low enough so newMessagesTokens >= minTokensPerPoint, but combining threshold will be higher
	  		const cfg = createConfig({
	  			messages,
	  			previousCachePointPlacements,
	  			modelInfo: { ...defaultModelInfo, minTokensPerCachePoint: 10, maxCachePoints: 2 },
	  			usePromptCache: true,
	  		})

	  		const strat = new MultiPointStrategy(cfg as any)
	  		const result = strat.determineOptimalCachePoints()

	  		// Combining should be deemed not beneficial -> logger should indicate keeping_existing_cache_points
	  		__testAugmentVitest_7816bcbcfc0c.expect(infoSpy).toHaveBeenCalled()
	  		const keepingCall = infoSpy.mock.calls.find((c: any) => c[1] && c[1].action === 'keeping_existing_cache_points')
	  		__testAugmentVitest_7816bcbcfc0c.expect(Boolean(keepingCall)).toBe(true)

	  		// And all previous placements that are still valid should be preserved
	  		__testAugmentVitest_7816bcbcfc0c.expect(result.messageCachePointPlacements?.some((p: any) => p.index === 1)).toBe(true)
	  		__testAugmentVitest_7816bcbcfc0c.expect(result.messageCachePointPlacements?.some((p: any) => p.index === 3)).toBe(true)
	  	} finally {
	  		(MultiPointStrategy as any).prototype.estimateTokenCount = originalEstimate
	  		infoSpy.mockRestore?.()
	  	}
	  })
	})
})

import * as __testAugmentVitest_7816bcbcfc0c from "vitest";

import * as __testAugmentTarget_055ee19ba3f8 from "../multi-point-strategy.js";

const __testAugmentLoadTarget_055ee19ba3f8 = async () => {
  __testAugmentVitest_7816bcbcfc0c.vi.doUnmock("../multi-point-strategy.js");
  __testAugmentVitest_7816bcbcfc0c.vi.resetModules();
  return import("../multi-point-strategy.js");
};
