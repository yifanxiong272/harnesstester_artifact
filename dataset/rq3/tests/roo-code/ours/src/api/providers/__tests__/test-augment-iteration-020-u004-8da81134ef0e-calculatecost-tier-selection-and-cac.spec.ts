import { t } from "i18next"
import { FunctionCallingConfigMode } from "@google/genai"

import { GeminiHandler } from "../gemini"
import type { ApiHandlerOptions } from "../../../shared/api"

describe("GeminiHandler backend support", () => {



  __testAugmentVitest_2bbf9f146b65.it("calculateCost tier selection and cache reads_round_020", async () => {
  	const options = { apiProvider: "gemini" } as ApiHandlerOptions
  	const handler = new GeminiHandler(options)

  	const info: any = {
  		// base prices (should be overridden by tier for our chosen tokens)
  		inputPrice: 0.01,
  		outputPrice: 0.02,
  		cacheReadsPrice: 0.005,
  		tiers: [
  			{ contextWindow: 100, inputPrice: 0.002, outputPrice: 0.003, cacheReadsPrice: 0.001 },
  		],
  	}

  	const result = handler.calculateCost({
  		info,
  		inputTokens: 50,
  		outputTokens: 10,
  		cacheReadTokens: 5,
  		reasoningTokens: 2,
  	})

  	// Compute expected based on selected tier (contextWindow 100 applies)
  	// uncachedInputTokens = 50 - 5 = 45
  	// input cost = 0.002 * (45 / 1_000_000)
  	// output billed tokens = 10 + 2 = 12 -> output cost = 0.003 * (12 / 1_000_000)
  	// cache read cost = 0.001 * (5 / 1_000_000)
  	const expected = 0.002 * (45 / 1_000_000) + 0.003 * (12 / 1_000_000) + 0.001 * (5 / 1_000_000)
  	__testAugmentVitest_2bbf9f146b65.expect(result).toBeCloseTo(expected, 12)
  })
})

import * as __testAugmentVitest_2bbf9f146b65 from "vitest";

const __testAugmentLoadTarget_5c0ad9f7168d = async () => {
  __testAugmentVitest_2bbf9f146b65.vi.doUnmock("../gemini.js");
  __testAugmentVitest_2bbf9f146b65.vi.resetModules();
  return import("../gemini.js");
};
