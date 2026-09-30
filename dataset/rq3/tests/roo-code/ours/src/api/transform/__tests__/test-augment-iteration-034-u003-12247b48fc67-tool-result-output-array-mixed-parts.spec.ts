// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("tool_result_output_array_mixed_parts_round_034", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	// tool_result that uses output (array) with mixed parts:
  	// - object with text
  	// - object with type: 'image' (should be replaced by placeholder)
  	// - string
  	// - number (coerced to string)
  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{
  					type: "tool_result",
  					tool_use_id: "tool-1",
  					output: [
  						{ text: "First" },
  						{ type: "image" },
  						"plain-string",
  						42,
  					],
  				},
  			],
  		},
  	]

  	const result = convertToBedrockConverseMessages(messages)
  	__testAugmentVitest_6514bd148b87.expect(result).toHaveLength(1)
  	const block = result[0].content?.[0] as any
  	__testAugmentVitest_6514bd148b87.expect("toolResult" in block).toBe(true)
  	const content = block.toolResult.content
  	__testAugmentVitest_6514bd148b87.expect(content).toEqual([
  		{ text: "First" },
  		{ text: "(see following message for image)" },
  		{ text: "plain-string" },
  		{ text: "42" },
  	])
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.status).toBe("success")
  	// toolUseId is short and should be preserved by sanitizeOpenAiCallId
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.toolUseId).toBe("tool-1")
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
