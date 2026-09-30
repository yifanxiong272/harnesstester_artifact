import { t } from "i18next"
import { FunctionCallingConfigMode } from "@google/genai"

import { GeminiHandler } from "../gemini"
import type { ApiHandlerOptions } from "../../../shared/api"

describe("GeminiHandler backend support", () => {



  __testAugmentVitest_2bbf9f146b65.it("filters reasoning meta messages_round_020", async () => {
  	const options = { apiProvider: "gemini" } as ApiHandlerOptions
  	const handler = new GeminiHandler(options)
  	// stub an empty async generator for the streaming client
  	const emptyStream = (async function* () {})()
  	const stub = __testAugmentVitest_2bbf9f146b65.vi.fn().mockReturnValue(emptyStream)
  	// @ts-ignore - access private client
  	handler["client"].models.generateContentStream = stub

  	// Provide a message that should be filtered out (provider-only reasoning meta)
  	await handler.createMessage("sys", [{ type: "reasoning" } as any]).next()

  	__testAugmentVitest_2bbf9f146b65.expect(stub).toHaveBeenCalled()
  	const params = stub.mock.calls[0][0]
  	// When only reasoning meta messages were provided, contents passed to the client are empty
  	__testAugmentVitest_2bbf9f146b65.expect(params.contents).toEqual([])
  })
})

import * as __testAugmentVitest_2bbf9f146b65 from "vitest";

const __testAugmentLoadTarget_5c0ad9f7168d = async () => {
  __testAugmentVitest_2bbf9f146b65.vi.doUnmock("../gemini.js");
  __testAugmentVitest_2bbf9f146b65.vi.resetModules();
  return import("../gemini.js");
};
