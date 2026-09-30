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





	  __testAugmentVitest_2bbf9f146b65.it("tool_choice_function_object_sets_allowed_single_round_020_pass_02", async () => {
	  	const { GeminiHandler } = __testAugmentTarget_5c0ad9f7168d
	  	const handler = new GeminiHandler({ apiProvider: "gemini" } as any)

	  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockReturnValue((async function* () {})())
	  	// @ts-ignore access private client
	  	handler["client"].models.generateContentStream = stub

	  	// Pass a tool_choice object describing a single function - should set allowedFunctionNames to that one name
	  	await handler.createMessage("sys", [] as any, { tool_choice: { type: "function", function: { name: "exec" } } } as any).next()

	  	const config = stub.mock.calls[0][0].config
	  	__testAugmentVitest_2bbf9f146b65.expect(config.toolConfig).toBeDefined()
	  	__testAugmentVitest_2bbf9f146b65.expect(config.toolConfig.functionCallingConfig.mode).toBe(FunctionCallingConfigMode.ANY)
	  	__testAugmentVitest_2bbf9f146b65.expect(config.toolConfig.functionCallingConfig.allowedFunctionNames).toEqual(["exec"])
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
