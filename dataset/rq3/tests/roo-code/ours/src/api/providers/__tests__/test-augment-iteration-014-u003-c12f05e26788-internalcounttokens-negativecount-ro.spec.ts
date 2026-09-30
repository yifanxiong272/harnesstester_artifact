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





	describe("countTokens", () => {
		beforeEach(() => {
			handler["client"] = mockLanguageModelChat
		})




	  __testAugmentVitest_1667f635d7ed.it("internalCountTokens_negativeCount_round_014", async () => {
	  	const { VsCodeLmHandler } = __testAugmentTarget_b385bc6a24be

	  	// Ensure client exists and prepare the client to return a negative token count
	  	handler["client"] = mockLanguageModelChat
	  	mockLanguageModelChat.countTokens.mockResolvedValueOnce(-5)

	  	const input = "some text"
	  	const result = await handler["internalCountTokens"](input)

	  	// Negative token counts should be treated as invalid and result in 0
	  	__testAugmentVitest_1667f635d7ed.expect(result).toBe(0)
	  	// Verify the underlying client was invoked with the string and a CancellationToken
	  	__testAugmentVitest_1667f635d7ed.expect(mockLanguageModelChat.countTokens).toHaveBeenCalledWith(input, __testAugmentVitest_1667f635d7ed.expect.any(Object))
	  })
	})

})

import * as __testAugmentVitest_1667f635d7ed from "vitest";

import * as __testAugmentTarget_b385bc6a24be from "../vscode-lm.js";

const __testAugmentLoadTarget_b385bc6a24be = async () => {
  __testAugmentVitest_1667f635d7ed.vi.doUnmock("../vscode-lm.js");
  __testAugmentVitest_1667f635d7ed.vi.resetModules();
  return import("../vscode-lm.js");
};
