import { t } from "i18next"
import { FunctionCallingConfigMode } from "@google/genai"

import { GeminiHandler } from "../gemini"
import type { ApiHandlerOptions } from "../../../shared/api"

describe("GeminiHandler backend support", () => {



	describe("allowedFunctionNames support", () => {
		const testTools = [
			{
				type: "function" as const,
				function: {
					name: "read_file",
					description: "Read a file",
					parameters: { type: "object", properties: {} },
				},
			},
			{
				type: "function" as const,
				function: {
					name: "write_to_file",
					description: "Write to a file",
					parameters: { type: "object", properties: {} },
				},
			},
			{
				type: "function" as const,
				function: {
					name: "execute_command",
					description: "Execute a command",
					parameters: { type: "object", properties: {} },
				},
			},
		]





	  __testAugmentVitest_2bbf9f146b65.it("emits_reasoning_parts_round_020_pass_02", async () => {
	  	const { GeminiHandler } = __testAugmentTarget_5c0ad9f7168d
	  	const handler = new GeminiHandler({ apiProvider: "gemini" } as any)

	  	// Stream that yields a candidate with a reasoning part (thought)
	  	const mockStream = async function* () {
	  		yield {
	  			candidates: [
	  				{
	  					content: {
	  						parts: [
	  							{ thought: true, text: "I have a thought" },
	  						],
	  					},
	  				},
	  			],
	  			usageMetadata: {},
	  		}
	  	}

	  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockReturnValue(mockStream())
	  	// @ts-ignore access private client
	  	handler["client"].models.generateContentStream = stub

	  	const outputs: any[] = []
	  	for await (const o of handler.createMessage("sys", [] as any)) {
	  		outputs.push(o)
	  	}

	  	__testAugmentVitest_2bbf9f146b65.expect(outputs.some((m) => m.type === "reasoning" && m.text === "I have a thought")).toBe(true)
	  })
	})
})

import * as __testAugmentVitest_2bbf9f146b65 from "vitest";

import * as __testAugmentTarget_5c0ad9f7168d from "../gemini.js";

const __testAugmentLoadTarget_5c0ad9f7168d = async () => {
  __testAugmentVitest_2bbf9f146b65.vi.doUnmock("../gemini.js");
  __testAugmentVitest_2bbf9f146b65.vi.resetModules();
  return import("../gemini.js");
};
