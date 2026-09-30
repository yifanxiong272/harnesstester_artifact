// npx vitest run __tests__/single-open-invariant.spec.ts

import { describe, it, expect, vi, beforeEach } from "vitest"
import { ClineProvider } from "../core/webview/ClineProvider"
import { API } from "../extension/api"
import * as ProfileValidatorMod from "../shared/ProfileValidator"

// Mock Task class used by ClineProvider to avoid heavy startup
vi.mock("../core/task/Task", () => {
	class TaskStub {
		public taskId: string
		public instanceId = "inst"
		public parentTask?: any
		public apiConfiguration: any
		public rootTask?: any
		constructor(opts: any) {
			this.taskId = opts.historyItem?.id ?? `task-${Math.random().toString(36).slice(2, 8)}`
			this.parentTask = opts.parentTask
			this.apiConfiguration = opts.apiConfiguration ?? { apiProvider: "anthropic" }
			opts.onCreated?.(this)
		}
		start() {}
		on() {}
		off() {}
		emit() {}
	}
	return { Task: TaskStub }
})

describe("Single-open-task invariant", () => {
	beforeEach(() => {
		vi.restoreAllMocks()
	})

	it("User-initiated create: closes existing before opening new", async () => {
		// Allow profile
		vi.spyOn(ProfileValidatorMod.ProfileValidator, "isProfileAllowed").mockReturnValue(true)

		const removeClineFromStack = vi.fn().mockResolvedValue(undefined)
		const addClineToStack = vi.fn().mockResolvedValue(undefined)

		const provider = {
			// Simulate an existing task present in stack
			clineStack: [{ taskId: "existing-1" }],
			setValues: vi.fn(),
			getState: vi.fn().mockResolvedValue({
				apiConfiguration: { apiProvider: "anthropic", consecutiveMistakeLimit: 0 },
				organizationAllowList: "*",
				enableCheckpoints: true,
				checkpointTimeout: 60,
				cloudUserInfo: null,
			}),
			removeClineFromStack,
			addClineToStack,
			setProviderProfile: vi.fn(),
			log: vi.fn(),
			getStateToPostToWebview: vi.fn(),
			providerSettingsManager: { getModeConfigId: vi.fn(), listConfig: vi.fn() },
			customModesManager: { getCustomModes: vi.fn().mockResolvedValue([]) },
			taskCreationCallback: vi.fn(),
			contextProxy: {
				extensionUri: {},
				setValue: vi.fn(),
				getValue: vi.fn(),
				setProviderSettings: vi.fn(),
				getProviderSettings: vi.fn(() => ({})),
			},
		} as unknown as ClineProvider

		await (ClineProvider.prototype as any).createTask.call(provider, "New task")

		expect(removeClineFromStack).toHaveBeenCalledTimes(1)
		expect(addClineToStack).toHaveBeenCalledTimes(1)
	})

	it("History resume path always closes current before rehydration (non-rehydrating case)", async () => {
		const removeClineFromStack = vi.fn().mockResolvedValue(undefined)
		const addClineToStack = vi.fn().mockResolvedValue(undefined)
		const updateGlobalState = vi.fn().mockResolvedValue(undefined)

		const provider = {
			getCurrentTask: vi.fn(() => undefined), // ensure not rehydrating
			removeClineFromStack,
			addClineToStack,
			updateGlobalState,
			log: vi.fn(),
			customModesManager: { getCustomModes: vi.fn().mockResolvedValue([]) },
			providerSettingsManager: {
				getModeConfigId: vi.fn().mockResolvedValue(undefined),
				listConfig: vi.fn().mockResolvedValue([]),
			},
			getState: vi.fn().mockResolvedValue({
				apiConfiguration: { apiProvider: "anthropic", consecutiveMistakeLimit: 0 },
				enableCheckpoints: true,
				checkpointTimeout: 60,
				experiments: {},
				cloudUserInfo: null,
				taskSyncEnabled: false,
			}),
			// Methods used by createTaskWithHistoryItem for pending edit cleanup
			getPendingEditOperation: vi.fn().mockReturnValue(undefined),
			clearPendingEditOperation: vi.fn(),
			context: { extension: { packageJSON: {} }, globalStorageUri: { fsPath: "/tmp" } },
			contextProxy: {
				extensionUri: {},
				getValue: vi.fn(),
				setValue: vi.fn(),
				setProviderSettings: vi.fn(),
				getProviderSettings: vi.fn(() => ({})),
			},
			postStateToWebview: vi.fn(),
		} as unknown as ClineProvider

		const historyItem = {
			id: "hist-1",
			number: 1,
			ts: Date.now(),
			task: "Task",
			tokensIn: 0,
			tokensOut: 0,
			totalCost: 0,
			workspace: "/tmp",
		}

		const task = await (ClineProvider.prototype as any).createTaskWithHistoryItem.call(provider, historyItem)
		expect(task).toBeTruthy()
		expect(removeClineFromStack).toHaveBeenCalledTimes(1)
		expect(addClineToStack).toHaveBeenCalledTimes(1)
	})

	it("IPC StartNewTask path closes current before new task", async () => {
		const removeClineFromStack = vi.fn().mockResolvedValue(undefined)
		const createTask = vi.fn().mockResolvedValue({ taskId: "ipc-1" })
		const provider = {
			context: {} as any,
			removeClineFromStack,
			postStateToWebview: vi.fn(),
			postMessageToWebview: vi.fn(),
			createTask,
			getValues: vi.fn(() => ({})),
			providerSettingsManager: { saveConfig: vi.fn() },
			on: vi.fn((ev: any, cb: any) => {
				if (ev === "taskCreated") {
					// no-op for this test
				}
				return provider
			}),
		} as unknown as ClineProvider

		const output = { appendLine: vi.fn() } as any
		const api = new API(output, provider, undefined, false)

		const taskId = await api.startNewTask({
			configuration: {},
			text: "hello",
			images: undefined,
			newTab: false,
		})

		expect(taskId).toBe("ipc-1")
		expect(removeClineFromStack).toHaveBeenCalledTimes(1)
		expect(createTask).toHaveBeenCalled()
	})

 it("resumeTask posts when view launched, logs when not, and emit triggers ipc.broadcast", async () => {
   const appendLine = vi.fn()
   const output = { appendLine } as any
 
   const createTaskWithHistoryItem = vi.fn().mockResolvedValue(undefined)
   const postMessageToWebview = vi.fn()
 
   const provider: any = {
     context: {},
     on: vi.fn(),
     getTaskWithId: vi.fn().mockResolvedValue({ historyItem: { id: "history-1" } }),
     createTaskWithHistoryItem,
     postMessageToWebview,
     viewLaunched: true,
     postStateToWebview: vi.fn(),
     providerSettingsManager: { saveConfig: vi.fn() },
     getValues: vi.fn(() => ({})),
     customModesManager: { getCustomModes: vi.fn().mockResolvedValue([]) },
   }
 
   const api = new API(output, provider, undefined, true)
 
   // Stub waitForWebviewLaunch to avoid waiting
   ;(api as any).waitForWebviewLaunch = vi.fn().mockResolvedValue(true)
 
   await api.resumeTask("history-1")
   expect(createTaskWithHistoryItem).toHaveBeenCalled()
   expect(postMessageToWebview).toHaveBeenCalledWith({ type: "action", action: "chatButtonClicked" })
 
   // Now simulate the webview not launching and ensure a log is emitted instead of a postMessage
   provider.viewLaunched = false
   ;(api as any).waitForWebviewLaunch = vi.fn().mockResolvedValue(false)
 
   await api.resumeTask("history-1")
   const logs = appendLine.mock.calls.map((c) => c[0]).join("\n")
   expect(logs).toContain("webview not launched after resume for task history-1")
 
   // verify emit uses ipc.broadcast when ipc present
   api["ipc"] = { broadcast: vi.fn() } as any
   api.emit("TaskStarted", "task-123")
   expect((api["ipc"].broadcast as any)).toHaveBeenCalled()
 })


 it("deleteQueuedMessage removes message when current exists; buttons invoke webview; isReady and logging behavior", async () => {
   const appendLine = vi.fn()
   const output = { appendLine } as any
 
   const removeMessage = vi.fn()
   const postMessageToWebview = vi.fn()
 
   const provider: any = {
     context: {},
     on: vi.fn(),
     viewLaunched: true,
     getCurrentTask: vi.fn(() => ({ messageQueueService: { removeMessage } })),
     postMessageToWebview,
     postStateToWebview: vi.fn(),
     providerSettingsManager: { saveConfig: vi.fn() },
     getValues: vi.fn(() => ({})),
     customModesManager: { getCustomModes: vi.fn().mockResolvedValue([]) },
   }
 
   const api = new API(output, provider, undefined, true)
 
   api.deleteQueuedMessage("msg-1")
   expect(removeMessage).toHaveBeenCalledWith("msg-1")
 
   await api.pressPrimaryButton()
   await api.pressSecondaryButton()
 
   expect(postMessageToWebview).toHaveBeenCalledWith({ type: "invoke", invoke: "primaryButtonClick" })
   expect(postMessageToWebview).toHaveBeenCalledWith({ type: "invoke", invoke: "secondaryButtonClick" })
   expect(api.isReady()).toBe(true)
 
   // When no current task exists, deletion should be ignored and logged
   provider.getCurrentTask = vi.fn(() => undefined)
   api.deleteQueuedMessage("msg-ignored")
 
   const joined = appendLine.mock.calls.map((c) => c[0]).join("\n")
   expect(joined).toContain("no current task; ignoring delete for messageId msg-ignored")
 })


 it("sendMessage in headless drops when no current task and submits when current exists (with logging)", async () => {
   const appendLine = vi.fn()
   const output = { appendLine } as any
 
   // Provider stub required by API constructor and used by sendMessage
   const submitUserMessage = vi.fn().mockResolvedValue(undefined)
   const provider: any = {
     context: {},
     on: vi.fn(), // safe no-op for registerListeners
     viewLaunched: false,
     getCurrentTask: vi.fn(() => undefined),
     postMessageToWebview: vi.fn(),
     postStateToWebview: vi.fn(),
     providerSettingsManager: { saveConfig: vi.fn() },
     getValues: vi.fn(() => ({})),
     customModesManager: { getCustomModes: vi.fn().mockResolvedValue([]) },
   }
 
   const api = new API(output, provider, undefined, true)
 
   // No current task => message dropped and a log entry should be emitted
   await api.sendMessage("hi")
   expect(appendLine).toHaveBeenCalled()
   const logged = appendLine.mock.calls.map((c) => c[0]).join("\n")
   expect(logged).toContain("[API#sendMessage] no current task in headless mode; message dropped")
 
   // Now make getCurrentTask return a task with submitUserMessage
   provider.getCurrentTask = vi.fn(() => ({ submitUserMessage }))
 
   await api.sendMessage("hey", ["img1"])
   expect(submitUserMessage).toHaveBeenCalledWith("hey", ["img1"])
 })


 it("outputChannelLog formats various argument types and handles non-serializable", async () => {
   const appendLine = vi.fn()
   const output = { appendLine } as any
 
   // Minimal provider stub so API constructor/registerListeners won't throw
   const provider: any = {
     context: {},
     on: vi.fn(), // no-op registration
     postStateToWebview: vi.fn(),
     postMessageToWebview: vi.fn(),
     getValues: vi.fn(() => ({})),
     providerSettingsManager: { saveConfig: vi.fn() },
     customModesManager: { getCustomModes: vi.fn().mockResolvedValue([]) },
   }
 
   // Enable logging so outputChannelLog is wired up
   const api = new API(output, provider, undefined, true)
 
   // Prepare diverse args:
   // - null and undefined top-level
   // - plain string
   // - Error instance
   // - an object that includes a BigInt and a function property so the replacer runs
   // - a circular object to force JSON.stringify to throw and trigger the fallback branch
   const objWithSpecial = { n: 1, big: 2n, fn: function myfn() {} }
   const circular: any = {}
   circular.self = circular
 
   // Call the private outputChannelLog to exercise formatting logic
   ;(api as any).outputChannelLog(null, undefined, "hello", new Error("myerr"), objWithSpecial, circular)
 
   const calls = appendLine.mock.calls.map((c) => c[0])
 
   // Assertions: ensure each expected rendered piece appears in the logged lines
   expect(calls).toContain("null")
   expect(calls).toContain("undefined")
   expect(calls).toContain("hello")
   // Error should be formatted and include the message
   expect(calls.some((s: string) => typeof s === "string" && s.includes("Error: myerr"))).toBeTruthy()
   // BigInt should be represented via the replacer
   expect(calls.some((s: string) => typeof s === "string" && s.includes("BigInt(2)"))).toBeTruthy()
   // Function name should be represented via the replacer
   expect(calls.some((s: string) => typeof s === "string" && s.includes("Function: myfn"))).toBeTruthy()
   // Non-serializable (circular) should trigger the fallback message
   expect(calls.some((s: string) => typeof s === "string" && s.includes("[Non-serializable object:"))).toBeTruthy()
 })

})
