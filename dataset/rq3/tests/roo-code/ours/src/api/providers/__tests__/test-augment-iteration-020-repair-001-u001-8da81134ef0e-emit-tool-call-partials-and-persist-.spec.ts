import { t } from "i18next"
import { FunctionCallingConfigMode } from "@google/genai"

import { GeminiHandler } from "../gemini"
import type { ApiHandlerOptions } from "../../../shared/api"

describe("GeminiHandler backend support", () => {



  __testAugmentVitest_2bbf9f146b65.it("emit-tool_call_partials_and_persist_thought_signature_and_response_round_020", async () => {
  	const options = { apiProvider: "gemini" } as ApiHandlerOptions
  	const handler = new GeminiHandler(options)

  	// Provide well-formed tool metadata so mapping to functionDeclarations succeeds
  	const metadata = {
  		tools: [
  			{
  				type: "function",
  				function: {
  					name: "doThing",
  					description: "Perform an action",
  					parameters: { type: "object", properties: {} },
  				},
  			},
  		],
  	} as any

  	const mockStream = async function* () {
  		yield {
  			// Provide a chunk that includes a candidate with a functionCall part and a thoughtSignature
  			candidates: [
  				{
  					finishReason: "completed",
  					content: {
  						parts: [
  							{
  								thoughtSignature: "sig-xyz",
  								functionCall: { name: "doThing", args: { x: 1 } },
  							},
  						],
  					},
  				},
  			],
  			// Response id at the chunk level is captured into lastResponseId by the handler
  			responseId: "resp-xyz",
  			usageMetadata: { promptTokenCount: 1, candidatesTokenCount: 1 },
  		}
  	}

  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockReturnValue(mockStream())
  	// @ts-ignore access private client
  	handler["client"].models.generateContentStream = stub

  	const outputs: any[] = []
  	for await (const o of handler.createMessage("sys", [] as any, metadata)) {
  		outputs.push(o)
  	}

  	// Expect two partials for the single function call: name then arguments
  	__testAugmentVitest_2bbf9f146b65.expect(outputs.filter((o) => o.type === "tool_call_partial")).toHaveLength(2)
  	__testAugmentVitest_2bbf9f146b65.expect(outputs[0]).toMatchObject({ type: "tool_call_partial", index: 0, name: "doThing" })
  	__testAugmentVitest_2bbf9f146b65.expect(outputs[1]).toMatchObject({ type: "tool_call_partial", index: 0, arguments: JSON.stringify({ x: 1 }) })

  	// Thought signature persisted
  	__testAugmentVitest_2bbf9f146b65.expect(handler.getThoughtSignature()).toBe("sig-xyz")
  	// ResponseId captured
  	__testAugmentVitest_2bbf9f146b65.expect(handler.getResponseId()).toBe("resp-xyz")
  })
})

import * as __testAugmentVitest_2bbf9f146b65 from "vitest";

const __testAugmentLoadTarget_5c0ad9f7168d = async () => {
  __testAugmentVitest_2bbf9f146b65.vi.doUnmock("../gemini.js");
  __testAugmentVitest_2bbf9f146b65.vi.resetModules();
  return import("../gemini.js");
};
