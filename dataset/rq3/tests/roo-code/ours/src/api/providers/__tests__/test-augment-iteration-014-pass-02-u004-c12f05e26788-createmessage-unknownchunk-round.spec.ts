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






  __testAugmentVitest_1667f635d7ed.it("createMessage_unknownChunk_round_014_pass_02", async () => {
  	// Arrange: ensure client is the mock and token counting returns quickly
  	handler["client"] = mockLanguageModelChat
  	mockLanguageModelChat.countTokens.mockResolvedValue(0)

  	// Stream yields an unknown chunk object (neither text nor tool-call)
  	mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
  		stream: (async function* () {
  			yield { unexpected: true } as any
  			return
  		})(),
  		text: (async function* () {
  			yield "ignored"
  			return
  		})(),
  	})

  	// Act: collect the stream output
  	const stream = handler.createMessage("sys", [{ role: "user", content: "hello" }])
  	const chunks: any[] = []
  	for await (const c of stream) {
  		chunks.push(c)
  	}

  	// Assert: unknown chunk type should be skipped and not crash the stream; only usage should be present
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
