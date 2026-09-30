// npx vitest src/core/assistant-message/__tests__/presentAssistantMessage-images.spec.ts

import { describe, it, expect, beforeEach, vi } from "vitest"
import { Anthropic } from "@anthropic-ai/sdk"
import { presentAssistantMessage } from "../presentAssistantMessage"
import { Task } from "../../task/Task"

// Mock dependencies

describe("presentAssistantMessage - Image Handling in Native Tool Calling", () => {
	let mockTask: any

	beforeEach(() => {
		// Create a mock Task with minimal properties needed for testing
		mockTask = {
			taskId: "test-task-id",
			instanceId: "test-instance",
			abort: false,
			presentAssistantMessageLocked: false,
			presentAssistantMessageHasPendingUpdates: false,
			currentStreamingContentIndex: 0,
			assistantMessageContent: [],
			userMessageContent: [],
			didCompleteReadingStream: false,
			didRejectTool: false,
			didAlreadyUseTool: false,
			consecutiveMistakeCount: 0,
			api: {
				getModel: () => ({ id: "test-model", info: {} }),
			},
			recordToolUsage: vi.fn(),
			toolRepetitionDetector: {
				check: vi.fn().mockReturnValue({ allowExecution: true }),
			},
			providerRef: {
				deref: () => ({
					getState: vi.fn().mockResolvedValue({
						mode: "code",
						customModes: [],
					}),
				}),
			},
			say: vi.fn().mockResolvedValue(undefined),
			ask: vi.fn().mockResolvedValue({ response: "yesButtonClicked" }),
		}

		// Add pushToolResultToUserContent method after mockTask is created so it can reference mockTask
		mockTask.pushToolResultToUserContent = vi.fn().mockImplementation((toolResult: any) => {
			const existingResult = mockTask.userMessageContent.find(
				(block: any) => block.type === "tool_result" && block.tool_use_id === toolResult.tool_use_id,
			)
			if (existingResult) {
				return false
			}
			mockTask.userMessageContent.push(toolResult)
			return true
		})
	})





  __testAugmentVitest_f68c26b88ef1.it("text undefined content calls say with undefined_round_007_pass_03", async () => {
  	// Arrange: text block where content is undefined
  	mockTask.assistantMessageContent = [
  		{
  			type: "text",
  			content: undefined,
  			partial: false,
  		},
  	]

  	// Spy on say
  	mockTask.say = __testAugmentVitest_f68c26b88ef1.vi.fn().mockResolvedValue(undefined)

  	// Act
  	await presentAssistantMessage(mockTask)

  	// Assert: say was called and the content argument is undefined
  	__testAugmentVitest_f68c26b88ef1.expect(mockTask.say).toHaveBeenCalled()
  	const args = (mockTask.say as any).mock.calls[0]
  	__testAugmentVitest_f68c26b88ef1.expect(args[0]).toBe("text")
  	__testAugmentVitest_f68c26b88ef1.expect(typeof args[1]).toBe("undefined")
  })
})

import * as __testAugmentVitest_f68c26b88ef1 from "vitest";

const __testAugmentLoadTarget_cd0434457219 = async () => {
  __testAugmentVitest_f68c26b88ef1.vi.doUnmock("../presentAssistantMessage.js");
  __testAugmentVitest_f68c26b88ef1.vi.resetModules();
  return import("../presentAssistantMessage.js");
};
