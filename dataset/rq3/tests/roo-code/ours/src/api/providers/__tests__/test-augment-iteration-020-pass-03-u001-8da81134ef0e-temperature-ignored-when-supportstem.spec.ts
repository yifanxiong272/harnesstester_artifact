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





	  __testAugmentVitest_2bbf9f146b65.it("temperature_ignored_when_supportsTemperature_false_round_020_pass_03", async () => {
	  	const { GeminiHandler } = __testAugmentTarget_5c0ad9f7168d
	  	const handler = new GeminiHandler({ apiProvider: "gemini" } as any)

	  	// Force getModel to return info.supportsTemperature = false (no defaultTemperature)
	  	handler.getModel = () => ({ id: "m", info: { supportsTemperature: false } } as any)

	  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockResolvedValue({ text: "ok" })
	  	// @ts-ignore access private client
	  	handler["client"].models.generateContent = stub

	  	await handler.completePrompt("hello world")

	  	// Inspect the config passed to the client's generateContent - temperature should be undefined
	  	const called = stub.mock.calls[0][0]
	  	__testAugmentVitest_2bbf9f146b65.expect(called).toBeDefined()
	  	__testAugmentVitest_2bbf9f146b65.expect(called.config).toBeDefined()
	  	__testAugmentVitest_2bbf9f146b65.expect(called.config.temperature).toBeUndefined()
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
