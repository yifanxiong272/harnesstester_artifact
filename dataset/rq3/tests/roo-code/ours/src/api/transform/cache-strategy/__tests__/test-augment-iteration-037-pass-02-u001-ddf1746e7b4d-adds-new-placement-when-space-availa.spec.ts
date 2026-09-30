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





	  __testAugmentVitest_7816bcbcfc0c.it("adds_new_placement_when_space_available_round_037_pass_02", async () => {
	  	const { MultiPointStrategy } = __testAugmentTarget_055ee19ba3f8

	  	// Patch estimateTokenCount to return deterministic small token counts so newMessagesTokens >= minTokensPerPoint
	  	const originalEstimate = (MultiPointStrategy as any).prototype.estimateTokenCount
	  	;(MultiPointStrategy as any).prototype.estimateTokenCount = function (_msg: any) {
	  		return 10
	  	}

	  	try {
	  		// Setup: previous placement at index 0, but remainingCachePoints will be larger than previousPlacements.length
	  		const messages = [
	  			{ role: "user", content: "u0" }, // previous placement here
	  			{ role: "assistant", content: "a1" },
	  			{ role: "user", content: "u2" }, // expected new placement here
	  			{ role: "assistant", content: "a3" },
	  		]

	  		const previousCachePointPlacements = [
	  			{ index: 0, type: "message", tokensCovered: 10 },
	  		]

	  		const cfg = createConfig({
	  			messages,
	  			previousCachePointPlacements,
	  			modelInfo: { ...defaultModelInfo, minTokensPerCachePoint: 20, maxCachePoints: 3 },
	  			usePromptCache: true,
	  		})

	  		const strat = new MultiPointStrategy(cfg as any)
	  		const result = strat.determineOptimalCachePoints()

	  		// Expect previous placement preserved
	  		__testAugmentVitest_7816bcbcfc0c.expect(result.messageCachePointPlacements?.some((p: any) => p.index === 0)).toBe(true)
	  		// And expect a new placement was added for the new messages (index 2)
	  		__testAugmentVitest_7816bcbcfc0c.expect(result.messageCachePointPlacements?.some((p: any) => p.index === 2)).toBe(true)
	  	} finally {
	  		(MultiPointStrategy as any).prototype.estimateTokenCount = originalEstimate
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
