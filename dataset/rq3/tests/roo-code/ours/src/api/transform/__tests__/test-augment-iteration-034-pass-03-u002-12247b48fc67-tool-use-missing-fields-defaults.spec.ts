// npx vitest run src/api/transform/__tests__/bedrock-converse-format.spec.ts

import { convertToBedrockConverseMessages } from "../bedrock-converse-format"
import { Anthropic } from "@anthropic-ai/sdk"
import { ContentBlock, ToolResultContentBlock } from "@aws-sdk/client-bedrock-runtime"
import { OPENAI_CALL_ID_MAX_LENGTH } from "../../../utils/tool-id"

describe("convertToBedrockConverseMessages", () => {










  __testAugmentVitest_6514bd148b87.it("tool_use_missing_fields_defaults_round_034_pass_03", () => {
  	const { convertToBedrockConverseMessages } = __testAugmentTarget_1cc7b8ede41a

  	// tool_use with no id, name, or input -> exercise messageBlock.id||"", name||"", input||{}
  	const messages: any[] = [
  		{
  			role: "assistant",
  			content: [
  				{ type: "tool_use" },
  			],
  		},
  	]

  	const result = convertToBedrockConverseMessages(messages)
  	__testAugmentVitest_6514bd148b87.expect(result).toHaveLength(1)
  	const block = result[0].content?.[0] as any
  	__testAugmentVitest_6514bd148b87.expect("toolUse" in block).toBe(true)
  	__testAugmentVitest_6514bd148b87.expect(block.toolUse).toBeDefined()
  	// name should default to empty string
  	__testAugmentVitest_6514bd148b87.expect(block.toolUse.name).toBe("")
  	// input should default to empty object
  	__testAugmentVitest_6514bd148b87.expect(block.toolUse.input).toEqual({})
  	// toolUseId is produced via sanitizeOpenAiCallId on empty input; ensure it's a string
  	__testAugmentVitest_6514bd148b87.expect(typeof block.toolUse.toolUseId).toBe("string")
  })
})

import * as __testAugmentVitest_6514bd148b87 from "vitest";

import * as __testAugmentTarget_1cc7b8ede41a from "../bedrock-converse-format.js";

const __testAugmentLoadTarget_1cc7b8ede41a = async () => {
  __testAugmentVitest_6514bd148b87.vi.doUnmock("../bedrock-converse-format.js");
  __testAugmentVitest_6514bd148b87.vi.resetModules();
  return import("../bedrock-converse-format.js");
};
