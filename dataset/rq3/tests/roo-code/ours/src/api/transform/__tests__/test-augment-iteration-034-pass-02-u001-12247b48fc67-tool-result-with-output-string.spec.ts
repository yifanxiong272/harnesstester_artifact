// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("tool_result_with_output_string_round_034_pass_02", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{
  					type: "tool_result",
  					tool_use_id: "out-1",
  					output: "Some plain output string",
  				},
  			],
  		},
  	]

  	const result = convertToBedrockConverseMessages(messages)
  	__testAugmentVitest_6514bd148b87.expect(result).toHaveLength(1)
  	const block = result[0].content?.[0] as any
  	__testAugmentVitest_6514bd148b87.expect(block).toBeDefined()
  	__testAugmentVitest_6514bd148b87.expect("toolResult" in block).toBe(true)
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.status).toBe("success")
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.content).toEqual([{ text: "Some plain output string" }])
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.toolUseId).toBe("out-1")
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
