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





	  __testAugmentVitest_2bbf9f146b65.it("captures_toolIdToName_map_round_020_pass_02", async () => {
	  	// Mock the converter so we can capture the toolIdToName Map passed into it
	  	__testAugmentVitest_2bbf9f146b65.vi.doMock("../../transform/gemini-format", () => ({
	  		convertAnthropicMessageToGemini: (message: any, opts: any) => {
	  			// stash on global so test can assert after createMessage runs
	  			;(global as any).__capturedToolIdToName = opts.toolIdToName
	  			return [] // return no contents to keep flow simple
	  		},
	  	}))

	  	// Load the target after installing the mock so our mock is used
	  	const mod = await __testAugmentLoadTarget_5c0ad9f7168d()
	  	const { GeminiHandler } = mod
	  	const handler = new GeminiHandler({ apiProvider: "gemini" } as any)

	  	// Stub the streaming client to an empty generator to avoid network
	  	const emptyStream = (async function* () {})()
	  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockReturnValue(emptyStream)
	  	// @ts-ignore access private client
	  	handler["client"].models.generateContentStream = stub

	  	// Provide a previous message containing a tool_use block so the map is populated
	  	const previousMessages = [
	  		{
	  			content: [
	  				{ type: "tool_use", id: "t1", name: "Reader" },
	  			],
	  		},
	  	]

	  	// Trigger createMessage (single .next() is sufficient because stub yields nothing)
	  	await handler.createMessage("sys", previousMessages as any).next()

	  	const captured = (global as any).__capturedToolIdToName
	  	__testAugmentVitest_2bbf9f146b65.expect(captured).toBeDefined()
	  	__testAugmentVitest_2bbf9f146b65.expect(captured instanceof Map).toBe(true)
	  	__testAugmentVitest_2bbf9f146b65.expect((captured as Map<string, string>).get("t1")).toBe("Reader")
	  })
	})
})

import * as __testAugmentVitest_2bbf9f146b65 from "vitest";

const __testAugmentLoadTarget_5c0ad9f7168d = async () => {
  __testAugmentVitest_2bbf9f146b65.vi.doUnmock("../gemini.js");
  __testAugmentVitest_2bbf9f146b65.vi.resetModules();
  return import("../gemini.js");
};
