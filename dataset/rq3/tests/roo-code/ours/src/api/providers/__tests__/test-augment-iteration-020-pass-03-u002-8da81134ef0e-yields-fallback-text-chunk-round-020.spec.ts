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





	  __testAugmentVitest_2bbf9f146b65.it("yields_fallback_text_chunk_round_020_pass_03", async () => {
	  	const { GeminiHandler } = __testAugmentTarget_5c0ad9f7168d
	  	const handler = new GeminiHandler({ apiProvider: "gemini" } as any)

	  	const mockStream = async function* () {
	  		yield { text: "legacy-text" }
	  	}

	  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockReturnValue(mockStream())
	  	// @ts-ignore access private client
	  	handler["client"].models.generateContentStream = stub

	  	const outputs: any[] = []
	  	for await (const chunk of handler.createMessage("sys", [] as any)) {
	  		outputs.push(chunk)
	  	}

	  	__testAugmentVitest_2bbf9f146b65.expect(outputs.some((m) => m.type === "text" && m.text === "legacy-text")).toBe(true)
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
