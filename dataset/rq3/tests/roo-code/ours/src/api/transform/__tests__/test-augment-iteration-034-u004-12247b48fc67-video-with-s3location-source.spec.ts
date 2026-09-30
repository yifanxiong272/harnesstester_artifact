// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("video_with_s3location_round_034", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	const messages: any[] = [
  		{
  			role: "assistant",
  			content: [
  				{
  					type: "video",
  					s3Location: {
  						uri: "s3://my-bucket/video.mp4",
  						bucketOwner: "owner-123",
  					},
  				},
  			],
  		},
  	]

  	const result = convertToBedrockConverseMessages(messages)
  	__testAugmentVitest_6514bd148b87.expect(result).toHaveLength(1)
  	const block = result[0].content?.[0] as any
  	__testAugmentVitest_6514bd148b87.expect("video" in block).toBe(true)
  	__testAugmentVitest_6514bd148b87.expect(block.video.format).toBe("mp4")
  	__testAugmentVitest_6514bd148b87.expect(block.video.source).toBeDefined()
  	__testAugmentVitest_6514bd148b87.expect(block.video.source.s3Location.uri).toBe("s3://my-bucket/video.mp4")
  	__testAugmentVitest_6514bd148b87.expect(block.video.source.s3Location.bucketOwner).toBe("owner-123")
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
