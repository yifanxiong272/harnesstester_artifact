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

	it("should preserve images in tool_result for native tool calling", async () => {
		// Set up a tool_use block with an ID (indicates native tool calling)
		const toolCallId = "tool_call_123"
		mockTask.assistantMessageContent = [
			{
				type: "tool_use",
				id: toolCallId, // ID indicates native tool calling
				name: "ask_followup_question",
				params: { question: "What do you see?" },
				nativeArgs: { question: "What do you see?", follow_up: [] },
			},
		]

		// Create a mock askApproval that includes images in the response
		const imageBlock: Anthropic.ImageBlockParam = {
			type: "image",
			source: {
				type: "base64",
				media_type: "image/png",
				data: "base64ImageData",
			},
		}

		mockTask.ask = vi.fn().mockResolvedValue({
			response: "yesButtonClicked",
			text: "I see a cat",
			images: ["data:image/png;base64,base64ImageData"],
		})

		// Execute presentAssistantMessage
		await presentAssistantMessage(mockTask)

		// Verify that userMessageContent was populated
		expect(mockTask.userMessageContent.length).toBeGreaterThan(0)

		// Find the tool_result block
		const toolResult = mockTask.userMessageContent.find(
			(item: any) => item.type === "tool_result" && item.tool_use_id === toolCallId,
		)

		expect(toolResult).toBeDefined()
		expect(toolResult.tool_use_id).toBe(toolCallId)

		// For native tool calling, tool_result content should be a string (text only)
		expect(typeof toolResult.content).toBe("string")
		expect(toolResult.content).toContain("I see a cat")

		// Images should be added as separate blocks AFTER the tool_result
		const imageBlocks = mockTask.userMessageContent.filter((item: any) => item.type === "image")
		expect(imageBlocks.length).toBeGreaterThan(0)
		expect(imageBlocks[0].source.data).toBe("base64ImageData")
	})

	it("should convert to string when no images are present (native tool calling)", async () => {
		// Set up a tool_use block with an ID (indicates native protocol)
		const toolCallId = "tool_call_456"
		mockTask.assistantMessageContent = [
			{
				type: "tool_use",
				id: toolCallId,
				name: "ask_followup_question",
				params: { question: "What is your name?" },
				nativeArgs: { question: "What is your name?", follow_up: [] },
			},
		]

		// Response with text but NO images
		mockTask.ask = vi.fn().mockResolvedValue({
			response: "yesButtonClicked",
			text: "My name is Alice",
			images: undefined,
		})

		await presentAssistantMessage(mockTask)

		const toolResult = mockTask.userMessageContent.find(
			(item: any) => item.type === "tool_result" && item.tool_use_id === toolCallId,
		)

		expect(toolResult).toBeDefined()

		// When no images, content should be a string
		expect(typeof toolResult.content).toBe("string")
	})

	it("should fail fast when tool_use is missing id (legacy/XML-style tool call)", async () => {
		// tool_use without an id is treated as legacy/XML-style tool call and must be rejected.
		mockTask.assistantMessageContent = [
			{
				type: "tool_use",
				name: "ask_followup_question",
				params: { question: "What do you see?" },
			},
		]

		mockTask.ask = vi.fn().mockResolvedValue({
			response: "yesButtonClicked",
			text: "I see a dog",
			images: ["data:image/png;base64,dogImageData"],
		})

		await presentAssistantMessage(mockTask)

		const textBlocks = mockTask.userMessageContent.filter((item: any) => item.type === "text")
		expect(textBlocks.length).toBeGreaterThan(0)
		expect(textBlocks.some((b: any) => String(b.text).includes("XML tool calls are no longer supported"))).toBe(
			true,
		)
		// Should not proceed to execute tool or add images as tool output.
		expect(mockTask.userMessageContent.some((item: any) => item.type === "image")).toBe(false)
	})

	it("should handle empty tool result gracefully", async () => {
		const toolCallId = "tool_call_789"
		mockTask.assistantMessageContent = [
			{
				type: "tool_use",
				id: toolCallId,
				name: "attempt_completion",
				params: { result: "Task completed" },
			},
		]

		// Empty response
		mockTask.ask = vi.fn().mockResolvedValue({
			response: "yesButtonClicked",
			text: undefined,
			images: undefined,
		})

		await presentAssistantMessage(mockTask)

		const toolResult = mockTask.userMessageContent.find(
			(item: any) => item.type === "tool_result" && item.tool_use_id === toolCallId,
		)

		expect(toolResult).toBeDefined()
		// Should have fallback text
		expect(toolResult.content).toBeTruthy()
	})

	describe("Multiple tool calls handling", () => {
		it("should send tool_result with is_error for skipped tools in native tool calling when didRejectTool is true", async () => {
			// Simulate multiple tool calls with native protocol (all have IDs)
			const toolCallId1 = "tool_call_001"
			const toolCallId2 = "tool_call_002"

			mockTask.assistantMessageContent = [
				{
					type: "tool_use",
					id: toolCallId1,
					name: "read_file",
					params: { path: "test.txt" },
				},
				{
					type: "tool_use",
					id: toolCallId2,
					name: "write_to_file",
					params: { path: "output.txt", content: "test" },
				},
			]

			// First tool is rejected
			mockTask.didRejectTool = true

			// Process the second tool (should be skipped)
			mockTask.currentStreamingContentIndex = 1
			await presentAssistantMessage(mockTask)

			// Find the tool_result for the second tool
			const toolResult = mockTask.userMessageContent.find(
				(item: any) => item.type === "tool_result" && item.tool_use_id === toolCallId2,
			)

			// Verify that a tool_result block was created (not a text block)
			expect(toolResult).toBeDefined()
			expect(toolResult.tool_use_id).toBe(toolCallId2)
			expect(toolResult.is_error).toBe(true)
			expect(toolResult.content).toContain("due to user rejecting a previous tool")

			// Ensure no text blocks were added for this rejection
			const textBlocks = mockTask.userMessageContent.filter(
				(item: any) => item.type === "text" && item.text.includes("due to user rejecting"),
			)
			expect(textBlocks.length).toBe(0)
		})

		it("should reject subsequent tool calls when a legacy/XML-style tool call is encountered", async () => {
			mockTask.assistantMessageContent = [
				{
					type: "tool_use",
					name: "read_file",
					params: { path: "test.txt" },
				},
				{
					type: "tool_use",
					name: "write_to_file",
					params: { path: "output.txt", content: "test" },
				},
			]

			// First tool is rejected
			mockTask.didRejectTool = true

			// Process the second tool (should be skipped)
			mockTask.currentStreamingContentIndex = 1
			await presentAssistantMessage(mockTask)

			const textBlocks = mockTask.userMessageContent.filter((item: any) => item.type === "text")
			expect(textBlocks.some((b: any) => String(b.text).includes("XML tool calls are no longer supported"))).toBe(
				true,
			)
			// Ensure no tool_result blocks were added
			expect(mockTask.userMessageContent.some((item: any) => item.type === "tool_result")).toBe(false)
		})

		it("should handle partial tool blocks when didRejectTool is true in native tool calling", async () => {
			const toolCallId = "tool_call_005"

			mockTask.assistantMessageContent = [
				{
					type: "tool_use",
					id: toolCallId,
					name: "write_to_file",
					params: { path: "output.txt", content: "test" },
					partial: true, // Partial tool block
				},
			]

			mockTask.didRejectTool = true

			await presentAssistantMessage(mockTask)

			// Find the tool_result
			const toolResult = mockTask.userMessageContent.find(
				(item: any) => item.type === "tool_result" && item.tool_use_id === toolCallId,
			)

			// Verify tool_result was created for partial block
			expect(toolResult).toBeDefined()
			expect(toolResult.is_error).toBe(true)
			expect(toolResult.content).toContain("was interrupted and not executed")
		})
	})

 it("marks_userMessageContentReady_and_unlocks_when_out_of_bounds_and_stream_complete", async () => {
   // Simulate that we've already advanced past the available content
   mockTask.assistantMessageContent = [{ type: "text", content: "should not be processed" }]
   mockTask.currentStreamingContentIndex = 1 // out of bounds
   mockTask.didCompleteReadingStream = true
   mockTask.presentAssistantMessageLocked = false
   mockTask.presentAssistantMessageHasPendingUpdates = false
   mockTask.userMessageContentReady = false
 
   await expect(presentAssistantMessage(mockTask)).resolves.toBeUndefined()
 
   // When out of bounds and stream complete, userMessageContentReady should be true
   expect(mockTask.userMessageContentReady).toBe(true)
   // And the function should not leave the lock engaged
   expect(mockTask.presentAssistantMessageLocked).toBe(false)
 })


 it("strips_thinking_tags_and_passes_partial_to_say", async () => {
   mockTask.currentStreamingContentIndex = 0
   mockTask.assistantMessageContent = [
     {
       type: "text",
       content: "<thinking>  partialOne </thinking> Final<thinking>middle</thinking>",
       partial: true,
     },
   ]
   // Clear any previous calls
   mockTask.say.mockClear()
   await presentAssistantMessage(mockTask)
   expect(mockTask.say).toHaveBeenCalled()
   // The first arg should be 'text', the second should be a string without thinking tags
   const callArgs = mockTask.say.mock.calls[0]
   expect(callArgs[0]).toBe("text")
   const contentArg = callArgs[1]
   expect(typeof contentArg).toBe("string")
   // Should not contain thinking tags and should contain the text segments
   expect(contentArg).not.toContain("<thinking>")
   expect(contentArg).not.toContain("</thinking>")
   expect(contentArg).toContain("partialOne")
   expect(contentArg).toContain("Final")
   expect(contentArg).toContain("middle")
   // The partial flag should be passed through as the 4th argument
   expect(callArgs[3]).toBe(true)
 })


 it("mcp_tool_use_skipped_when_previous_tool_was_rejected", async () => {
   const mcpId = "mcp_call_42"
   mockTask.assistantMessageContent = [
     {
       type: "mcp_tool_use",
       id: mcpId,
       serverName: "sanitized_srv",
       toolName: "the_tool",
       name: "sanitized_srv_the_tool",
       arguments: { a: 1 },
       partial: false,
     },
   ]
 
   mockTask.currentStreamingContentIndex = 0
   // Simulate that a previous tool was rejected
   mockTask.didRejectTool = true
 
   // Ensure pushToolResultToUserContent exists (beforeEach already adds one, but be explicit)
   if (!mockTask.pushToolResultToUserContent) {
     mockTask.pushToolResultToUserContent = vi.fn().mockImplementation((toolResult: any) => {
       mockTask.userMessageContent.push(toolResult)
       return true
     })
   }
 
   await presentAssistantMessage(mockTask)
 
   const tr = mockTask.userMessageContent.find(
     (b: any) => b.type === "tool_result" && b.tool_use_id === mcpId,
   )
   expect(tr).toBeDefined()
   expect(tr.is_error).toBe(true)
   expect(String(tr.content)).toContain("Skipping MCP tool")
 })


 it("sets_pending_updates_when_locked", async () => {
   // Start with locked = true and pendingUpdates = false
   mockTask.presentAssistantMessageLocked = true
   mockTask.presentAssistantMessageHasPendingUpdates = false
   mockTask.currentStreamingContentIndex = 0
   mockTask.assistantMessageContent = []
 
   // Should return quickly and set pending updates flag
   await presentAssistantMessage(mockTask)
 
   expect(mockTask.presentAssistantMessageHasPendingUpdates).toBe(true)
   // The lock should remain true (function returns early)
   expect(mockTask.presentAssistantMessageLocked).toBe(true)
 })


 it("aborts_immediately_when_task_is_aborted", async () => {
   // Reuse mockTask from beforeEach but mark as aborted
   mockTask.abort = true
   // Ensure minimal other state
   mockTask.presentAssistantMessageLocked = false
   mockTask.currentStreamingContentIndex = 0
   mockTask.assistantMessageContent = []
 
   await expect(presentAssistantMessage(mockTask)).rejects.toThrow(
     `[Task#presentAssistantMessage] task ${mockTask.taskId}.${mockTask.instanceId} aborted`,
   )
 })

})
