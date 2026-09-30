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






  __testAugmentVitest_1667f635d7ed.it("createClient_defaultModel_sendRequest_stream_round_014_pass_03", async () => {
  	// Make selectChatModels return an empty list to force the default minimal model path
  	;(vscode.lm.selectChatModels as any).mockResolvedValueOnce([])

  	const client = await handler["createClient"]({})
  	__testAugmentVitest_1667f635d7ed.expect(client).toBeDefined()
  	__testAugmentVitest_1667f635d7ed.expect(client.id).toBe("default-lm")

  	// Call the default client's sendRequest and consume the stream
  	const response = await client.sendRequest([], {}, new vscode.CancellationTokenSource().token)
  	const parts: string[] = []
  	for await (const part of response.stream) {
  		if (part instanceof vscode.LanguageModelTextPart) {
  			parts.push(part.value)
  		}
  	}

  	__testAugmentVitest_1667f635d7ed.expect(parts.length).toBeGreaterThan(0)
  	__testAugmentVitest_1667f635d7ed.expect(parts[0]).toEqual(expect.stringContaining("Language model functionality is limited"))
  })
})

import * as __testAugmentVitest_1667f635d7ed from "vitest";

const __testAugmentLoadTarget_b385bc6a24be = async () => {
  __testAugmentVitest_1667f635d7ed.vi.doUnmock("../vscode-lm.js");
  __testAugmentVitest_1667f635d7ed.vi.resetModules();
  return import("../vscode-lm.js");
};
