// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("image_with_unsupported_format_throws_round_034", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{
  					type: "image",
  					source: {
  						type: "base64",
  						data: "AAA", // string branch for image conversion path
  						media_type: "image/bmp", // unsupported format -> should throw
  					},
  				},
  			],
  		},
  	]

  	__testAugmentVitest_6514bd148b87.expect(() => convertToBedrockConverseMessages(messages)).toThrow("Unsupported image format: bmp")
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
