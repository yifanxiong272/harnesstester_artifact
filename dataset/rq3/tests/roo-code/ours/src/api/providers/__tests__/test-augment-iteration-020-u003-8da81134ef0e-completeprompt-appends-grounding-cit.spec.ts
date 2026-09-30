import { t } from "i18next"
import { FunctionCallingConfigMode } from "@google/genai"

import { GeminiHandler } from "../gemini"
import type { ApiHandlerOptions } from "../../../shared/api"

describe("GeminiHandler backend support", () => {



  __testAugmentVitest_2bbf9f146b65.it("completePrompt appends grounding citations_round_020", async () => {
  	const options = { apiProvider: "gemini" } as ApiHandlerOptions
  	const handler = new GeminiHandler(options)

  	const candidate = {
  		groundingMetadata: {
  			groundingChunks: [{ web: { uri: "https://example.test/page", title: "Example Page" } }],
  		},
  	}

  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockResolvedValue({ text: "the answer", candidates: [candidate] })
  	// @ts-ignore access private client
  	handler["client"].models.generateContent = stub

  	const res = await handler.completePrompt("prompt text")
  	__testAugmentVitest_2bbf9f146b65.expect(res).toContain("the answer")
  	// Should include the localized sources label and a markdown link to the grounding URI
  	__testAugmentVitest_2bbf9f146b65.expect(res).toContain(t("common:errors.gemini.sources"))
  	__testAugmentVitest_2bbf9f146b65.expect(res).toContain("[1](https://example.test/page)")
  })
})

import * as __testAugmentVitest_2bbf9f146b65 from "vitest";

const __testAugmentLoadTarget_5c0ad9f7168d = async () => {
  __testAugmentVitest_2bbf9f146b65.vi.doUnmock("../gemini.js");
  __testAugmentVitest_2bbf9f146b65.vi.resetModules();
  return import("../gemini.js");
};
