// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("image_with_uint8array_source_round_034", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	// Provide a Uint8Array as the image data (branch where data is not a base64 string)
  	const bytes = new Uint8Array([1, 2, 3, 255])
  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{
  					type: "image",
  					source: {
  						type: "base64",
  						data: bytes, // Uint8Array branch
  						media_type: "image/png",
  					},
  				},
  			],
  		},
  	]

  	const result = convertToBedrockConverseMessages(messages)
  	__testAugmentVitest_6514bd148b87.expect(result).toHaveLength(1)
  	const block = result[0].content?.[0] as any
  	__testAugmentVitest_6514bd148b87.expect(block).toBeDefined()
  	__testAugmentVitest_6514bd148b87.expect("image" in block).toBe(true)
  	__testAugmentVitest_6514bd148b87.expect(block.image).toBeDefined()
  	// Format should be parsed from media_type
  	__testAugmentVitest_6514bd148b87.expect(block.image.format).toBe("png")
  	// The returned bytes should equal the original Uint8Array
  	__testAugmentVitest_6514bd148b87.expect(block.image.source.bytes).toEqual(bytes)
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
