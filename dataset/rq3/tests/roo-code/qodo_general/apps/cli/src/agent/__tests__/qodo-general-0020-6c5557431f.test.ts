// pnpm --filter @roo-code/cli test src/agent/__tests__/extension-host.test.ts

import { EventEmitter } from "events"
import fs from "fs"

import type { ExtensionMessage, WebviewMessage } from "@roo-code/types"

import { DEFAULT_FLAGS } from "@/types/index.js"

import { type ExtensionHostOptions, ExtensionHost } from "../extension-host.js"
import { ExtensionClient } from "../extension-client.js"
import { AgentLoopState } from "../agent-state.js"
import { OutputManager } from "../output-manager.js"

vi.mock("@roo-code/vscode-shim", () => ({
	createVSCodeAPI: vi.fn(() => ({
		context: { extensionPath: "/test/extension" },
	})),
	setRuntimeConfigValues: vi.fn(),
}))

vi.mock("@/lib/storage/index.js", () => ({
	createEphemeralStorageDir: vi.fn(() => Promise.resolve("/tmp/roo-cli-test-ephemeral")),
}))

/**
 * Create a test ExtensionHost with default options.
 */
function createTestHost({
	mode = "code",
	provider = "openrouter",
	model = "test-model",
	...options
}: Partial<ExtensionHostOptions> = {}): ExtensionHost {
	return new ExtensionHost({
		mode,
		user: null,
		provider,
		model,
		workspacePath: "/test/workspace",
		extensionPath: "/test/extension",
		ephemeral: false,
		debug: false,
		exitOnComplete: false,
		...options,
	})
}

// Type for accessing private members
type PrivateHost = Record<string, unknown>

/**
 * Helper to access private members for testing
 */
function getPrivate<T>(host: ExtensionHost, key: string): T {
	return (host as unknown as PrivateHost)[key] as T
}

/**
 * Helper to set private members for testing
 */
function setPrivate(host: ExtensionHost, key: string, value: unknown): void {
	;(host as unknown as PrivateHost)[key] = value
}

/**
 * Helper to call private methods for testing
 * This uses a more permissive type to avoid TypeScript errors with private methods
 */
function callPrivate<T>(host: ExtensionHost, method: string, ...args: unknown[]): T {
	const fn = (host as unknown as PrivateHost)[method] as ((...a: unknown[]) => T) | undefined
	if (!fn) throw new Error(`Method ${method} not found`)
	return fn.apply(host, args)
}

/**
 * Helper to spy on private methods
 * This uses a more permissive type to avoid TypeScript errors with vi.spyOn on private methods
 */
function spyOnPrivate(host: ExtensionHost, method: string) {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	return vi.spyOn(host as any, method)
}

describe("ExtensionHost", () => {
	const initialRooCliRuntimeEnv = process.env.ROO_CLI_RUNTIME

	beforeEach(() => {
		vi.resetAllMocks()
		if (initialRooCliRuntimeEnv === undefined) {
			delete process.env.ROO_CLI_RUNTIME
		} else {
			process.env.ROO_CLI_RUNTIME = initialRooCliRuntimeEnv
		}
		// Clean up globals
		delete (global as Record<string, unknown>).vscode
		delete (global as Record<string, unknown>).__extensionHost
	})

	afterAll(() => {
		if (initialRooCliRuntimeEnv === undefined) {
			delete process.env.ROO_CLI_RUNTIME
		} else {
			process.env.ROO_CLI_RUNTIME = initialRooCliRuntimeEnv
		}
	})

	describe("constructor", () => {
		it("should store options correctly", () => {
			const options: ExtensionHostOptions = {
				mode: "code",
				workspacePath: "/my/workspace",
				extensionPath: "/my/extension",
				user: null,
				apiKey: "test-key",
				provider: "openrouter",
				model: "test-model",
				ephemeral: false,
				debug: false,
				exitOnComplete: false,
				integrationTest: true, // Set explicitly for testing
			}

			const host = new ExtensionHost(options)

			// Options are stored as-is
			const storedOptions = getPrivate<ExtensionHostOptions>(host, "options")
			expect(storedOptions.mode).toBe(options.mode)
			expect(storedOptions.workspacePath).toBe(options.workspacePath)
			expect(storedOptions.extensionPath).toBe(options.extensionPath)
			expect(storedOptions.integrationTest).toBe(true)
		})

		it("should be an EventEmitter instance", () => {
			const host = createTestHost()
			expect(host).toBeInstanceOf(EventEmitter)
		})

		it("should initialize with default state values", () => {
			const host = createTestHost()

			expect(getPrivate(host, "isReady")).toBe(false)
			expect(getPrivate(host, "vscode")).toBeNull()
			expect(getPrivate(host, "extensionModule")).toBeNull()
		})

		it("should initialize managers", () => {
			const host = createTestHost()

			// Should have client, outputManager, promptManager, and askDispatcher
			expect(getPrivate(host, "client")).toBeDefined()
			expect(getPrivate(host, "outputManager")).toBeDefined()
			expect(getPrivate(host, "promptManager")).toBeDefined()
			expect(getPrivate(host, "askDispatcher")).toBeDefined()
		})

		it("should mark process as CLI runtime", () => {
			delete process.env.ROO_CLI_RUNTIME
			createTestHost()
			expect(process.env.ROO_CLI_RUNTIME).toBe("1")
		})

		it("should set execaShellPath in initialSettings when terminalShell is provided", () => {
			const host = createTestHost({ terminalShell: "/bin/bash" })
			const emitSpy = vi.spyOn(host, "emit")
			host.markWebviewReady()
			const updateSettingsCall = emitSpy.mock.calls.find(
				(call) =>
					call[0] === "webviewMessage" &&
					typeof call[1] === "object" &&
					call[1] !== null &&
					(call[1] as WebviewMessage).type === "updateSettings",
			)
			expect(updateSettingsCall).toBeDefined()
			const payload = updateSettingsCall?.[1] as WebviewMessage
			expect(payload.updatedSettings?.execaShellPath).toBe("/bin/bash")
		})
	})

	describe("webview provider registration", () => {
		it("should register webview provider without throwing", () => {
			const host = createTestHost()
			const mockProvider = { resolveWebviewView: vi.fn() }

			// registerWebviewProvider is now a no-op, just ensure it doesn't throw
			expect(() => {
				host.registerWebviewProvider("test-view", mockProvider)
			}).not.toThrow()
		})

		it("should unregister webview provider without throwing", () => {
			const host = createTestHost()
			const mockProvider = { resolveWebviewView: vi.fn() }

			host.registerWebviewProvider("test-view", mockProvider)

			// unregisterWebviewProvider is now a no-op, just ensure it doesn't throw
			expect(() => {
				host.unregisterWebviewProvider("test-view")
			}).not.toThrow()
		})

		it("should handle unregistering non-existent provider gracefully", () => {
			const host = createTestHost()

			expect(() => {
				host.unregisterWebviewProvider("non-existent")
			}).not.toThrow()
		})
	})

	describe("webview ready state", () => {
		describe("isInInitialSetup", () => {
			it("should return true before webview is ready", () => {
				const host = createTestHost()
				expect(host.isInInitialSetup()).toBe(true)
			})

			it("should return false after markWebviewReady is called", () => {
				const host = createTestHost()
				host.markWebviewReady()
				expect(host.isInInitialSetup()).toBe(false)
			})
		})

		describe("markWebviewReady", () => {
			it("should set isReady to true", () => {
				const host = createTestHost()
				host.markWebviewReady()
				expect(getPrivate(host, "isReady")).toBe(true)
			})

			it("should send webviewDidLaunch message", () => {
				const host = createTestHost()
				const emitSpy = vi.spyOn(host, "emit")

				host.markWebviewReady()

				expect(emitSpy).toHaveBeenCalledWith("webviewMessage", { type: "webviewDidLaunch" })
			})

			it("should send updateSettings message", () => {
				const host = createTestHost()
				const emitSpy = vi.spyOn(host, "emit")

				host.markWebviewReady()

				// Check that updateSettings was called
				const updateSettingsCall = emitSpy.mock.calls.find(
					(call) =>
						call[0] === "webviewMessage" &&
						typeof call[1] === "object" &&
						call[1] !== null &&
						(call[1] as WebviewMessage).type === "updateSettings",
				)
				expect(updateSettingsCall).toBeDefined()
			})

			it("should force terminalShellIntegrationDisabled when terminalShell is provided", () => {
				const host = createTestHost({ terminalShell: "/bin/bash" })
				const emitSpy = vi.spyOn(host, "emit")

				host.markWebviewReady()

				const updateSettingsCall = emitSpy.mock.calls.find(
					(call) =>
						call[0] === "webviewMessage" &&
						typeof call[1] === "object" &&
						call[1] !== null &&
						(call[1] as WebviewMessage).type === "updateSettings",
				)

				expect(updateSettingsCall).toBeDefined()
				const payload = updateSettingsCall?.[1] as WebviewMessage
				expect(payload.type).toBe("updateSettings")
				expect(payload.updatedSettings?.terminalShellIntegrationDisabled).toBe(true)
			})
		})
	})

	describe("sendToExtension", () => {
		it("should throw error when extension not ready", () => {
			const host = createTestHost()
			const message: WebviewMessage = { type: "requestModes" }

			expect(() => {
				host.sendToExtension(message)
			}).toThrow("You cannot send messages to the extension before it is ready")
		})

		it("should emit webviewMessage event when webview is ready", () => {
			const host = createTestHost()
			const emitSpy = vi.spyOn(host, "emit")
			const message: WebviewMessage = { type: "requestModes" }

			host.markWebviewReady()
			emitSpy.mockClear() // Clear the markWebviewReady calls
			host.sendToExtension(message)

			expect(emitSpy).toHaveBeenCalledWith("webviewMessage", message)
		})

		it("should not throw when webview is ready", () => {
			const host = createTestHost()

			host.markWebviewReady()

			expect(() => {
				host.sendToExtension({ type: "requestModes" })
			}).not.toThrow()
		})
	})

	describe("message handling via client", () => {
		it("should forward extension messages to the client", () => {
			const host = createTestHost()
			const client = getPrivate(host, "client") as ExtensionClient

			// Simulate extension message.
			host.emit("extensionWebviewMessage", {
				type: "state",
				state: { clineMessages: [] },
			} as unknown as ExtensionMessage)

			// Message listener is set up in activate(), which we can't easily call in unit tests.
			// But we can verify the client exists and has the handleMessage method.
			expect(typeof client.handleMessage).toBe("function")
		})
	})

	describe("public agent state API", () => {
		it("should return agent state from getAgentState()", () => {
			const host = createTestHost()
			const state = host.getAgentState()

			expect(state).toBeDefined()
			expect(state.state).toBeDefined()
			expect(state.isWaitingForInput).toBeDefined()
			expect(state.isRunning).toBeDefined()
		})

		it("should return isWaitingForInput() status", () => {
			const host = createTestHost()
			expect(typeof host.isWaitingForInput()).toBe("boolean")
		})
	})

	describe("quiet mode", () => {
		describe("setupQuietMode", () => {
			it("should not modify console when integrationTest is true", () => {
				// By default, constructor sets integrationTest = true
				const host = createTestHost()
				const originalLog = console.log

				callPrivate(host, "setupQuietMode")

				// Console should not be modified since integrationTest is true
				expect(console.log).toBe(originalLog)
			})

			it("should suppress console when integrationTest is false", () => {
				// Capture the real console.log before any host is created
				const originalLog = console.log

				// Create host with integrationTest: true to prevent constructor from suppressing
				const host = createTestHost({ integrationTest: true })

				// Override integrationTest to false to test suppression
				const options = getPrivate<ExtensionHostOptions>(host, "options")
				options.integrationTest = false

				callPrivate(host, "setupQuietMode")

				// Console should be modified (suppressed)
				expect(console.log).not.toBe(originalLog)

				// Restore for other tests
				callPrivate(host, "restoreConsole")
			})

			it("should preserve console.error even when suppressing", () => {
				const host = createTestHost()
				const originalError = console.error

				// Override integrationTest to false
				const options = getPrivate<ExtensionHostOptions>(host, "options")
				options.integrationTest = false

				callPrivate(host, "setupQuietMode")

				expect(console.error).toBe(originalError)

				callPrivate(host, "restoreConsole")
			})
		})

		describe("restoreConsole", () => {
			it("should restore original console methods when suppressed", () => {
				// Capture the real console.log before any host is created
				const originalLog = console.log

				// Create host with integrationTest: true to prevent constructor from suppressing
				const host = createTestHost({ integrationTest: true })

				// Override integrationTest to false to actually suppress
				const options = getPrivate<ExtensionHostOptions>(host, "options")
				options.integrationTest = false

				callPrivate(host, "setupQuietMode")
				callPrivate(host, "restoreConsole")

				expect(console.log).toBe(originalLog)
			})

			it("should handle case where console was not suppressed", () => {
				const host = createTestHost()

				expect(() => {
					callPrivate(host, "restoreConsole")
				}).not.toThrow()
			})
		})
	})

	describe("dispose", () => {
		let host: ExtensionHost

		beforeEach(() => {
			host = createTestHost()
		})

		it("should remove message listener", async () => {
			const listener = vi.fn()
			setPrivate(host, "messageListener", listener)
			host.on("extensionWebviewMessage", listener)

			await host.dispose()

			expect(getPrivate(host, "messageListener")).toBeNull()
		})

		it("should call extension deactivate if available", async () => {
			const deactivateMock = vi.fn()
			setPrivate(host, "extensionModule", {
				deactivate: deactivateMock,
			})

			await host.dispose()

			expect(deactivateMock).toHaveBeenCalled()
		})

		it("should clear vscode reference", async () => {
			setPrivate(host, "vscode", { context: {} })

			await host.dispose()

			expect(getPrivate(host, "vscode")).toBeNull()
		})

		it("should clear extensionModule reference", async () => {
			setPrivate(host, "extensionModule", {})

			await host.dispose()

			expect(getPrivate(host, "extensionModule")).toBeNull()
		})

		it("should delete global vscode", async () => {
			;(global as Record<string, unknown>).vscode = {}

			await host.dispose()

			expect((global as Record<string, unknown>).vscode).toBeUndefined()
		})

		it("should delete global __extensionHost", async () => {
			;(global as Record<string, unknown>).__extensionHost = {}

			await host.dispose()

			expect((global as Record<string, unknown>).__extensionHost).toBeUndefined()
		})

		it("should call restoreConsole", async () => {
			const restoreConsoleSpy = spyOnPrivate(host, "restoreConsole")

			await host.dispose()

			expect(restoreConsoleSpy).toHaveBeenCalled()
		})

		it("should clear ROO_CLI_RUNTIME on dispose when it was previously unset", async () => {
			delete process.env.ROO_CLI_RUNTIME
			host = createTestHost()
			expect(process.env.ROO_CLI_RUNTIME).toBe("1")

			await host.dispose()

			expect(process.env.ROO_CLI_RUNTIME).toBeUndefined()
		})

		it("should restore prior ROO_CLI_RUNTIME value on dispose", async () => {
			process.env.ROO_CLI_RUNTIME = "preexisting-value"
			host = createTestHost()
			expect(process.env.ROO_CLI_RUNTIME).toBe("1")

			await host.dispose()

			expect(process.env.ROO_CLI_RUNTIME).toBe("preexisting-value")
		})
	})

	describe("runTask", () => {
		it("should send newTask message when called", async () => {
			const host = createTestHost()
			host.markWebviewReady()

			const emitSpy = vi.spyOn(host, "emit")
			const client = getPrivate(host, "client") as ExtensionClient

			// Start the task (will hang waiting for completion)
			const taskPromise = host.runTask("test prompt")

			// Emit completion to resolve the promise via the client's emitter
			const taskCompletedEvent = {
				success: true,
				stateInfo: {
					state: AgentLoopState.IDLE,
					isWaitingForInput: false,
					isRunning: false,
					isStreaming: false,
					requiredAction: "start_task" as const,
					description: "Task completed",
				},
			}
			setTimeout(() => client.getEmitter().emit("taskCompleted", taskCompletedEvent), 10)

			await taskPromise

			expect(emitSpy).toHaveBeenCalledWith("webviewMessage", { type: "newTask", text: "test prompt" })
		})

		it("should include taskId when provided", async () => {
			const host = createTestHost()
			host.markWebviewReady()

			const emitSpy = vi.spyOn(host, "emit")
			const client = getPrivate(host, "client") as ExtensionClient

			const taskPromise = host.runTask("test prompt", "task-123")

			const taskCompletedEvent = {
				success: true,
				stateInfo: {
					state: AgentLoopState.IDLE,
					isWaitingForInput: false,
					isRunning: false,
					isStreaming: false,
					requiredAction: "start_task" as const,
					description: "Task completed",
				},
			}
			setTimeout(() => client.getEmitter().emit("taskCompleted", taskCompletedEvent), 10)

			await taskPromise

			expect(emitSpy).toHaveBeenCalledWith("webviewMessage", {
				type: "newTask",
				text: "test prompt",
				taskId: "task-123",
			})
		})

		it("should resolve when taskCompleted is emitted on client", async () => {
			const host = createTestHost()
			host.markWebviewReady()

			const client = getPrivate(host, "client") as ExtensionClient
			const taskPromise = host.runTask("test prompt")

			// Emit completion after a short delay via the client's emitter
			const taskCompletedEvent = {
				success: true,
				stateInfo: {
					state: AgentLoopState.IDLE,
					isWaitingForInput: false,
					isRunning: false,
					isStreaming: false,
					requiredAction: "start_task" as const,
					description: "Task completed",
				},
			}
			setTimeout(() => client.getEmitter().emit("taskCompleted", taskCompletedEvent), 10)

			await expect(taskPromise).resolves.toBeUndefined()
		})

		it("should send showTaskWithId for resumeTask and resolve on completion", async () => {
			const host = createTestHost()
			host.markWebviewReady()

			const emitSpy = vi.spyOn(host, "emit")
			const client = getPrivate(host, "client") as ExtensionClient

			const taskPromise = host.resumeTask("task-abc")

			const taskCompletedEvent = {
				success: true,
				stateInfo: {
					state: AgentLoopState.IDLE,
					isWaitingForInput: false,
					isRunning: false,
					isStreaming: false,
					requiredAction: "start_task" as const,
					description: "Task completed",
				},
			}
			setTimeout(() => client.getEmitter().emit("taskCompleted", taskCompletedEvent), 10)

			await taskPromise

			expect(emitSpy).toHaveBeenCalledWith("webviewMessage", { type: "showTaskWithId", text: "task-abc" })
		})
	})

	describe("initial settings", () => {
		it("should set mode from options", () => {
			const host = createTestHost({ mode: "architect" })

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.mode).toBe("architect")
		})

		it("should use default consecutiveMistakeLimit when not provided", () => {
			const host = createTestHost()

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.consecutiveMistakeLimit).toBe(DEFAULT_FLAGS.consecutiveMistakeLimit)
		})

		it("should set consecutiveMistakeLimit from options", () => {
			const host = createTestHost({ consecutiveMistakeLimit: 8 })

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.consecutiveMistakeLimit).toBe(8)
		})

		it("should enable auto-approval in non-interactive mode", () => {
			const host = createTestHost({ nonInteractive: true })

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.autoApprovalEnabled).toBe(true)
			expect(initialSettings.alwaysAllowReadOnly).toBe(true)
			expect(initialSettings.alwaysAllowWrite).toBe(true)
			expect(initialSettings.alwaysAllowExecute).toBe(true)
		})

		it("should disable auto-approval in interactive mode", () => {
			const host = createTestHost({ nonInteractive: false })

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.autoApprovalEnabled).toBe(false)
		})

		it("should set reasoning effort when specified", () => {
			const host = createTestHost({ reasoningEffort: "high" })

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.enableReasoningEffort).toBe(true)
			expect(initialSettings.reasoningEffort).toBe("high")
		})

		it("should disable reasoning effort when set to disabled", () => {
			const host = createTestHost({ reasoningEffort: "disabled" })

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.enableReasoningEffort).toBe(false)
		})

		it("should not set reasoning effort when unspecified", () => {
			const host = createTestHost({ reasoningEffort: "unspecified" })

			const initialSettings = getPrivate<Record<string, unknown>>(host, "initialSettings")
			expect(initialSettings.enableReasoningEffort).toBeUndefined()
			expect(initialSettings.reasoningEffort).toBeUndefined()
		})
	})

	describe("ephemeral mode", () => {
		it("should store ephemeral option correctly", () => {
			const host = createTestHost({ ephemeral: true })

			const options = getPrivate<ExtensionHostOptions>(host, "options")
			expect(options.ephemeral).toBe(true)
		})

		it("should default ephemeralStorageDir to null", () => {
			const host = createTestHost()

			expect(getPrivate(host, "ephemeralStorageDir")).toBeNull()
		})

		it("should clean up ephemeral storage directory on dispose", async () => {
			const host = createTestHost({ ephemeral: true })

			// Set up a mock ephemeral storage directory
			const mockEphemeralDir = "/tmp/roo-cli-test-ephemeral-cleanup"
			setPrivate(host, "ephemeralStorageDir", mockEphemeralDir)

			// Mock fs.promises.rm
			const rmMock = vi.spyOn(fs.promises, "rm").mockResolvedValue(undefined)

			await host.dispose()

			expect(rmMock).toHaveBeenCalledWith(mockEphemeralDir, { recursive: true, force: true })
			expect(getPrivate(host, "ephemeralStorageDir")).toBeNull()

			rmMock.mockRestore()
		})

		it("should not clean up when ephemeralStorageDir is null", async () => {
			const host = createTestHost()

			// ephemeralStorageDir is null by default
			expect(getPrivate(host, "ephemeralStorageDir")).toBeNull()

			const rmMock = vi.spyOn(fs.promises, "rm").mockResolvedValue(undefined)

			await host.dispose()

			// rm should not be called when there's no ephemeral storage
			expect(rmMock).not.toHaveBeenCalled()

			rmMock.mockRestore()
		})

		it("should handle ephemeral storage cleanup errors gracefully", async () => {
			const host = createTestHost({ ephemeral: true })

			// Set up a mock ephemeral storage directory
			setPrivate(host, "ephemeralStorageDir", "/tmp/roo-cli-test-ephemeral-error")

			// Mock fs.promises.rm to throw an error
			const rmMock = vi.spyOn(fs.promises, "rm").mockRejectedValue(new Error("Cleanup failed"))

			// dispose should not throw even if cleanup fails
			await expect(host.dispose()).resolves.toBeUndefined()

			rmMock.mockRestore()
		})

		it("should not affect normal mode when ephemeral is false", () => {
			const host = createTestHost({ ephemeral: false })

			const options = getPrivate<ExtensionHostOptions>(host, "options")
			expect(options.ephemeral).toBe(false)
			expect(getPrivate(host, "ephemeralStorageDir")).toBeNull()
		})
	})

 it("outputCompletionResult_writes_header_and_respects_previously_streamed_flag", () => {
   // Case A: completionResultStreamed is false -> write header + text
   const writesA: string[] = []
   const fakeStdoutA = {
     write: (s: string) => {
       writesA.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderrA = { write: (_: string) => true } as unknown as NodeJS.WriteStream
   const managerA = new OutputManager({ stdout: fakeStdoutA, stderr: fakeStderrA })
 
   managerA.outputCompletionResult(4, "done")
 
   // Should write header + space + text + newline as a single write from output(...)
   expect(writesA).toEqual(["\n[task complete] done\n"])
   expect(managerA.isAlreadyDisplayed(4)).toBe(true)
 
   // Case B: completionResultStreamed is true due to prior say:completion_result partial stream
   const writesB: string[] = []
   const fakeStdoutB = {
     write: (s: string) => {
       writesB.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderrB = { write: (_: string) => true } as unknown as NodeJS.WriteStream
   const managerB = new OutputManager({ stdout: fakeStdoutB, stderr: fakeStderrB })
 
   // Stream a partial completion_result (say) to set completionResultStreamed = true
   managerB.outputMessage({ ts: 5, type: "say", say: "completion_result", text: "part", partial: true })
 
   // Now call outputCompletionResult for the same ts; should output only the task-complete header
   managerB.outputCompletionResult(5, "fulltext")
 
   // Expect initial assistant header+partial, then a single "[task complete]" line (no duplicate text)
   expect(writesB).toEqual(["\n[assistant] ", "part", "\n[task complete]\n"])
   expect(managerB.isAlreadyDisplayed(5)).toBe(true)
 })


 it("command_output_partial_then_complete_writes_delta_and_finishes_stream", () => {
   const writes: string[] = []
   const fakeStdout = {
     write: (s: string) => {
       writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderr = {
     write: (_: string) => true,
   } as unknown as NodeJS.WriteStream
 
   const manager = new OutputManager({ stdout: fakeStdout, stderr: fakeStderr })
 
   // Stream a partial command_output via say
   manager.outputMessage({ ts: 3, type: "say", say: "command_output", text: "cmd", partial: true })
 
   // Now send the complete command_output; should output only the delta and then newline
   manager.outputMessage({ ts: 3, type: "say", say: "command_output", text: "cmd finished", partial: false })
 
   // Expect initial header + partial, then delta (" finished"), then newline from finishStream
   expect(writes).toEqual(["\n[command output] ", "cmd", " finished", "\n"])
 
   // The message should now be fully displayed
   expect(manager.isAlreadyDisplayed(3)).toBe(true)
 })


 it("streamContent_initial_and_delta_write_only_new_characters", () => {
   const writes: string[] = []
   const fakeStdout = {
     write: (s: string) => {
       writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderr = {
     write: (_: string) => true,
   } as unknown as NodeJS.WriteStream
 
   const manager = new OutputManager({ stdout: fakeStdout, stderr: fakeStderr })
 
   // initial stream - should write header and the initial text
   manager.streamContent(2, "first", "[hdr]")
 
   // extended text that starts with previous text - should write only the delta
   manager.streamContent(2, "first-more", "[hdr]")
 
   expect(writes).toEqual(["\n[hdr] ", "first", "-more"])
 
   // The manager should still consider ts=2 as currently streaming
   expect(manager.getCurrentlyStreamingTs()).toBe(2)
 })


 it("outputTextMessage_writes_complete_message_when_not_streamed", () => {
   const writes: string[] = []
   const fakeStdout = {
     write: (s: string) => {
       writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderr = {
     write: (_: string) => true,
   } as unknown as NodeJS.WriteStream
 
   const manager = new OutputManager({ stdout: fakeStdout, stderr: fakeStderr })
 
   // Call with skipFirstUserMessage = false to ensure output is not skipped
   manager.outputMessage({ ts: 1, type: "say", say: "text", text: "hello world", partial: false }, false)
 
   // Expect a single combined write from output("\n[assistant]", text)
   expect(writes).toEqual(["\n[assistant] hello world\n"])
 
   // Message should be marked as fully displayed
   expect(manager.isAlreadyDisplayed(1)).toBe(true)
 
   // Currently streaming should be null (no active stream)
   expect(manager.getCurrentlyStreamingTs()).toBeNull()
 
   // streamedContent should have an entry for this ts with headerShown true
   const streamedContent = (manager as unknown as Record<string, unknown>).streamedContent as Map<number, unknown>
   expect(streamedContent.get(1)).toBeDefined()
   // @ts-expect-error access internals for test assertions
   expect((streamedContent.get(1) as any).headerShown).toBe(true)
 })


 it("outputCommandOutput writes complete non-streamed output with header and newline", () => {
   const writes: string[] = []
   const fakeStdout = {
     write: (s: string) => {
       writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderr = {
     write: (_: string) => true,
   } as unknown as NodeJS.WriteStream
 
   const manager = new OutputManager({ stdout: fakeStdout, stderr: fakeStderr })
 
   // Send a complete (non-partial) command_output message
   manager.outputMessage({ ts: 303, type: "say", say: "command_output", text: "ls -la output", partial: false })
 
   // Should write header, content, newline
   expect(writes).toEqual(["\n[command output] ", "ls -la output", "\n"])
   // Marked as displayed
   expect(manager.isAlreadyDisplayed(303)).toBe(true)
 })


 it("outputText skips first user message when skipFirstUserMessage is true", () => {
   const writes: string[] = []
   const fakeStdout = {
     write: (s: string) => {
       writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderr = {
     write: (_: string) => true,
   } as unknown as NodeJS.WriteStream
 
   const manager = new OutputManager({ stdout: fakeStdout, stderr: fakeStderr })
 
   // First user "text" message should be skipped (no writes) but marked displayed
   manager.outputMessage({ ts: 202, type: "say", say: "text", text: "user prompt", partial: false }, true)
 
   expect(writes).toEqual([]) // nothing written to stdout
   // It should be marked as displayed (complete)
   expect(manager.isAlreadyDisplayed(202)).toBe(true)
   // No streaming in progress
   expect(manager.isCurrentlyStreaming()).toBe(false)
 })


 it("outputReasoning streams partial and writes delta on completion", () => {
   const writes: string[] = []
   const fakeStdout = {
     write: (s: string) => {
       writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const fakeStderr = {
     write: (_: string) => true,
   } as unknown as NodeJS.WriteStream
 
   const manager = new OutputManager({ stdout: fakeStdout, stderr: fakeStderr })
 
   // Send partial reasoning message (starts stream)
   manager.outputMessage({ ts: 101, type: "say", say: "reasoning", text: "hello", partial: true })
 
   // Now send completed reasoning message that extends the partial text
   manager.outputMessage({ ts: 101, type: "say", say: "reasoning", text: "hello world", partial: false })
 
   // Expect initial header+text, then only the delta (" world"), then newline from finishStream
   expect(writes).toEqual(["\n[reasoning] ", "hello", " world", "\n"])
 
   // Streaming should be finished
   expect(manager.isCurrentlyStreaming()).toBe(false)
   expect(manager.getCurrentlyStreamingTs()).toBeNull()
 
   // The message should be recorded as fully displayed
   expect(manager.isAlreadyDisplayed(101)).toBe(true)
 })


 it("should write say:error to stderr and handle streamed completion_result then outputCompletionResult", () => {
   const mockStdout = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const mockStderr = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
 
   const om = new OutputManager({ stdout: mockStdout, stderr: mockStderr })
 
   // say:error should write to stderr and set displayedMessages
   const errMsg = {
     type: "say",
     ts: 20,
     say: "error",
     text: "boom",
     partial: false,
   }
   om.outputMessage(errMsg as any)
   expect((mockStderr as any).writes).toContain("\n[error] boom\n")
   expect(om.isAlreadyDisplayed(20)).toBe(true)
 
   // Now test completion_result streamed via say (partial)
   const partialCompletion = {
     type: "say",
     ts: 30,
     say: "completion_result",
     text: "Streamed",
     partial: true,
   }
   om.outputMessage(partialCompletion as any)
   // Header + streamed text should be written to stdout
   expect((mockStdout as any).writes[0]).toBe("\n[assistant] ")
   expect((mockStdout as any).writes[1]).toBe("Streamed")
 
   // When outputCompletionResult is called after streaming, only the task-complete label should be output (no text)
   om.outputCompletionResult(30, "Streamed")
   // The output method writes a label + newline; check that this exact label appears
   expect((mockStdout as any).writes).toContain("\n[task complete]\n")
 
   // If called again for the same ts it's already displayed - no duplicate
   const before = (mockStdout as any).writes.length
   om.outputCompletionResult(30, "Streamed")
   expect((mockStdout as any).writes.length).toBe(before)
 })


 it("should output complete ask:command_output when not streamed and not duplicate", () => {
   const mockStdout = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const mockStderr = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
 
   const om = new OutputManager({ stdout: mockStdout, stderr: mockStderr })
 
   const msg = {
     type: "ask",
     ts: 10,
     ask: "command_output",
     text: "cmd result",
     partial: false,
   }
   om.outputMessage(msg as any)
 
   const writes = (mockStdout as any).writes
   // Expect header, text and trailing newline (written via writeRaw sequentially)
   expect(writes[0]).toBe("\n[command output] ")
   expect(writes[1]).toBe("cmd result")
   expect(writes[2]).toBe("\n")
 
   // Calling again with same ts should not produce additional output because it's already displayed
   om.outputMessage(msg as any)
   expect((mockStdout as any).writes.length).toBe(3)
   expect(om.isAlreadyDisplayed(10)).toBe(true)
 })


 it("should stream assistant text partial then complete with delta and finish stream", () => {
   const mockStdout = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const mockStderr = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
 
   const om = new OutputManager({ stdout: mockStdout, stderr: mockStderr })
 
   // Ensure there's at least one displayed message so skipFirstUserMessage doesn't early-return
   om.markDisplayed(1, "prev", false)
 
   // Send partial assistant text
   const partialMsg = {
     type: "say",
     ts: 2,
     say: "text",
     text: "Hel",
     partial: true,
   }
   om.outputMessage(partialMsg as any)
 
   // Expect header + initial text (stream start)
   expect((mockStdout as any).writes[0]).toBe("\n[assistant] ")
   expect((mockStdout as any).writes[1]).toBe("Hel")
   expect(om.isCurrentlyStreaming()).toBe(true)
   expect(om.getCurrentlyStreamingTs()).toBe(2)
 
   // Complete message with more text - should output delta "lo" then newline
   const completeMsg = {
     type: "say",
     ts: 2,
     say: "text",
     text: "Hello",
     partial: false,
   }
   om.outputMessage(completeMsg as any)
 
   // After completion, delta and newline should have been written
   const writes = (mockStdout as any).writes
   // Last two writes should be the delta and newline (order: header, initial, delta, newline)
   expect(writes).toContain("lo")
   expect(writes).toContain("\n")
   expect(om.isCurrentlyStreaming()).toBe(false)
   expect(om.getCurrentlyStreamingTs()).toBeNull()
   expect(om.isAlreadyDisplayed(2)).toBe(true)
 })


 it("should write to streams, respect disabled flag, and manage basic state helpers", () => {
   // simple mock streams that record writes
   const mockStdout = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
   const mockStderr = {
     writes: [] as string[],
     write(this: any, s: string) {
       this.writes.push(String(s))
       return true
     },
   } as unknown as NodeJS.WriteStream
 
   // Disabled manager should not write anything
   const disabledOm = new OutputManager({ disabled: true, stdout: mockStdout, stderr: mockStderr })
   disabledOm.output("L", "T")
   disabledOm.outputError("E", "TE")
   disabledOm.writeRaw("raw")
   expect((mockStdout as any).writes.length).toBe(0)
   expect((mockStderr as any).writes.length).toBe(0)
 
   // Enabled manager should write to the provided streams
   const om = new OutputManager({ stdout: mockStdout, stderr: mockStderr })
   expect(om.isCurrentlyStreaming()).toBe(false)
   expect(om.getCurrentlyStreamingTs()).toBeNull()
 
   om.output("label")
   om.output("label2", "text2")
   expect((mockStdout as any).writes).toContain("label\n")
   expect((mockStdout as any).writes).toContain("label2 text2\n")
 
   om.outputError("err", "msg")
   expect((mockStderr as any).writes).toContain("err msg\n")
 
   om.writeRaw("raw!")
   expect((mockStdout as any).writes).toContain("raw!")
 
   // markDisplayed / isAlreadyDisplayed
   expect(om.isAlreadyDisplayed(42)).toBe(false)
   om.markDisplayed(42, "some", false)
   expect(om.isAlreadyDisplayed(42)).toBe(true)
 
   // first-partial logging helpers
   expect(om.hasLoggedFirstPartial(7)).toBe(false)
   om.setLoggedFirstPartial(7)
   expect(om.hasLoggedFirstPartial(7)).toBe(true)
   om.clearLoggedFirstPartial(7)
   expect(om.hasLoggedFirstPartial(7)).toBe(false)
 
   // clear resets state
   om.clear()
   expect(om.isAlreadyDisplayed(42)).toBe(false)
   expect(om.isCurrentlyStreaming()).toBe(false)
   expect(om.getCurrentlyStreamingTs()).toBeNull()
 })

})
