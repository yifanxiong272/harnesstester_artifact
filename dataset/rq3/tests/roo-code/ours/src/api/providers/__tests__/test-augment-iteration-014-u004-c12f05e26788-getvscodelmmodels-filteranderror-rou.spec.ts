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




	  __testAugmentVitest_1667f635d7ed.it("getVsCodeLmModels_filterAndError_round_014", async () => {
	  	const { getVsCodeLmModels } = __testAugmentTarget_b385bc6a24be

	  	// 1) Filtering behavior: include a normal model and a blacklisted one
	  	;(vscode.lm.selectChatModels as any).mockResolvedValueOnce([
	  		{ id: "good-model", name: "Good Model" },
	  		{ id: "claude-3.7-sonnet", name: "Blacklisted Model" },
	  	])

	  	const models = await getVsCodeLmModels()
	  	const ids = models.map((m: any) => m.id)
	  	__testAugmentVitest_1667f635d7ed.expect(ids).toEqual(["good-model"])

	  	// 2) Error fallback: when selectChatModels throws we should get an empty array
	  	;(vscode.lm.selectChatModels as any).mockRejectedValueOnce(new Error("select-failed"))
	  	const modelsOnError = await getVsCodeLmModels()
	  	__testAugmentVitest_1667f635d7ed.expect(modelsOnError).toEqual([])
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
