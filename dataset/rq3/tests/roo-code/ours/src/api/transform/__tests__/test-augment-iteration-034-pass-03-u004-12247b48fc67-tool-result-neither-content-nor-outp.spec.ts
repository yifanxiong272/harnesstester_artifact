// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("tool_result_neither_content_nor_output_defaults_to_empty_round_034_pass_03", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	// tool_result with no content and no output -> default case produces empty-string content
  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{ type: "tool_result", tool_use_id: "empty-1" },
  			],
  		},
  	]

  	const result = convertToBedrockConverseMessages(messages)
  	const block = result[0].content?.[0] as any
  	__testAugmentVitest_6514bd148b87.expect("toolResult" in block).toBe(true)
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.content).toEqual([{ text: "" }])
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.status).toBe("success")
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
