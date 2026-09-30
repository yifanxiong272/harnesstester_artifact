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





  __testAugmentVitest_f68c26b88ef1.it("mcp_tool_use_rejected_pushes_tool_result_round_007", async () => {
  	// Arrange: native MCP tool use with id, but a previous tool was rejected
  	const toolCallId = "mcp_42"
  	mockTask.assistantMessageContent = [
  		{
  			type: "mcp_tool_use",
  			id: toolCallId,
  			serverName: "srv",
  			toolName: "do_something",
  			partial: false,
  		},
  	]
  	mockTask.currentStreamingContentIndex = 0
  	mockTask.didRejectTool = true
  	// ensure a fresh output array
  	mockTask.userMessageContent = []

  	// Act
  	await presentAssistantMessage(mockTask)

  	// Assert: a structured tool_result was pushed for the MCP tool and marked as an error
  	const toolResult = mockTask.userMessageContent.find((b: any) => b.type === "tool_result" && b.tool_use_id === toolCallId)
  	__testAugmentVitest_f68c26b88ef1.expect(toolResult).toBeDefined()
  	__testAugmentVitest_f68c26b88ef1.expect(toolResult.is_error).toBe(true)
  	__testAugmentVitest_f68c26b88ef1.expect(String(toolResult.content)).toContain("Skipping MCP tool")
  });
})

import * as __testAugmentVitest_f68c26b88ef1 from "vitest";

const __testAugmentLoadTarget_cd0434457219 = async () => {
  __testAugmentVitest_f68c26b88ef1.vi.doUnmock("../presentAssistantMessage.js");
  __testAugmentVitest_f68c26b88ef1.vi.resetModules();
  return import("../presentAssistantMessage.js");
};
