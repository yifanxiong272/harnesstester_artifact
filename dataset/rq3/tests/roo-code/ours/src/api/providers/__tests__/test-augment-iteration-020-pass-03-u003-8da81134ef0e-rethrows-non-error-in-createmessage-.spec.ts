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





	  __testAugmentVitest_2bbf9f146b65.it("rethrows_non_error_in_createMessage_round_020_pass_03", async () => {
	  	const { GeminiHandler } = __testAugmentTarget_5c0ad9f7168d
	  	const handler = new GeminiHandler({ apiProvider: "gemini" } as any)

	  	// Make the streaming client reject with a non-Error value
	  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockRejectedValue("not-an-error")
	  	// @ts-ignore access private client
	  	handler["client"].models.generateContentStream = stub

	  	// The generator.next() promise should reject with the original non-Error value
	  	await __testAugmentVitest_2bbf9f146b65.expect(handler.createMessage("sys", [] as any).next()).rejects.toEqual("not-an-error")
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
