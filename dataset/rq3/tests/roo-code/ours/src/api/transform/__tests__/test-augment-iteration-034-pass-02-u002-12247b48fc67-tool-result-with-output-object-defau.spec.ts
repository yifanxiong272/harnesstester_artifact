// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("tool_result_with_output_object_default_round_034_pass_02", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	// output is an object (neither string nor array) -> default fallback path
  	const messages: any[] = [
  		{
  			role: "user",
  			content: [
  				{
  					type: "tool_result",
  					tool_use_id: "obj-1",
  					output: { nested: true, value: 123 },
  				},
  			],
  		},
  	]

  	const result = convertToBedrockConverseMessages(messages)
  	const block = result[0].content?.[0] as any
  	__testAugmentVitest_6514bd148b87.expect("toolResult" in block).toBe(true)
  	// Default case stringifies the output object via String(output) -> "[object Object]"
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.content).toEqual([{ text: "[object Object]" }])
  	__testAugmentVitest_6514bd148b87.expect(block.toolResult.toolUseId).toBe("obj-1")
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
