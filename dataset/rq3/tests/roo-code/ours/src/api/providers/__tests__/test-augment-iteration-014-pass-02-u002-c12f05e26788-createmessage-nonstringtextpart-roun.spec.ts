import type { Mock } from "vitest"

// Mocks must come first, before imports
vi.mock("vscode", () => {
	class MockLanguageModelTextPart {
		type = "text"
		constructor(public value: string) {}
	}

	class MockLanguageModelToolCallPart {
		type = "tool_call"
		constructor(
			public callId: string,
			public name: string,
			public input: any,
		) {}
	}

	return {
		workspace: {
			onDidChangeConfiguration: vi.fn((_callback) => ({
				dispose: vi.fn(),
			})),
		},
		CancellationTokenSource: vi.fn(() => ({
			token: {
				isCancellationRequested: false,
				onCancellationRequested: vi.fn(),
			},
			cancel: vi.fn(),
			dispose: vi.fn(),
		})),
		CancellationError: class CancellationError extends Error {
			constructor() {
				super("Operation cancelled")
				this.name = "CancellationError"
			}
		},
		LanguageModelChatMessage: {
			Assistant: vi.fn((content) => ({
				role: "assistant",
				content: Array.isArray(content) ? content : [new MockLanguageModelTextPart(content)],
			})),
			User: vi.fn((content) => ({
				role: "user",
				content: Array.isArray(content) ? content : [new MockLanguageModelTextPart(content)],
			})),
		},
		LanguageModelTextPart: MockLanguageModelTextPart,
		LanguageModelToolCallPart: MockLanguageModelToolCallPart,
		lm: {
			selectChatModels: vi.fn(),
		},
	}
})

import * as vscode from "vscode"
import { VsCodeLmHandler } from "../vscode-lm"
import type { ApiHandlerOptions } from "../../../shared/api"
import type { Anthropic } from "@anthropic-ai/sdk"

const mockLanguageModelChat = {
	id: "test-model",
	name: "Test Model",
	vendor: "test-vendor",
	family: "test-family",
	version: "1.0",
	maxInputTokens: 4096,
	sendRequest: vi.fn(),
	countTokens: vi.fn(),
}

describe("VsCodeLmHandler", () => {
	let handler: VsCodeLmHandler
	const defaultOptions: ApiHandlerOptions = {
		vsCodeLmModelSelector: {
			vendor: "test-vendor",
			family: "test-family",
		},
	}

	beforeEach(() => {
		vi.clearAllMocks()
		handler = new VsCodeLmHandler(defaultOptions)
	})

	afterEach(() => {
		handler.dispose()
	})






  __testAugmentVitest_1667f635d7ed.it("createMessage_nonStringTextPart_round_014_pass_02", async () => {
  	// Arrange: ensure client is the mock and token counting returns quickly
  	handler["client"] = mockLanguageModelChat
  	mockLanguageModelChat.countTokens.mockResolvedValue(0)

  	// Make the model send a text part whose value is NOT a string (should be ignored)
  	mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
  		stream: (async function* () {
  			yield new vscode.LanguageModelTextPart({ not: "a-string" } as any)
  			return
  		})(),
  		text: (async function* () {
  			yield "ignored"
  			return
  		})(),
  	})

  	// Act: create the message stream and collect chunks
  	const stream = handler.createMessage("sys", [{ role: "user", content: "hi" }])
  	const chunks: any[] = []
  	for await (const c of stream) {
  		chunks.push(c)
  	}

  	// Assert: non-string text part should be skipped, leaving only the final usage chunk
  	__testAugmentVitest_1667f635d7ed.expect(chunks.length).toBe(1)
  	__testAugmentVitest_1667f635d7ed.expect(chunks[0]).toMatchObject({ type: "usage" })
  })
})

import * as __testAugmentVitest_1667f635d7ed from "vitest";

const __testAugmentLoadTarget_b385bc6a24be = async () => {
  __testAugmentVitest_1667f635d7ed.vi.doUnmock("../vscode-lm.js");
  __testAugmentVitest_1667f635d7ed.vi.resetModules();
  return import("../vscode-lm.js");
};
