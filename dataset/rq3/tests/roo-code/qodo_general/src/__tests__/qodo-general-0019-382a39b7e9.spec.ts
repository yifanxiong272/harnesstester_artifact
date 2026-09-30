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

 it("sendMessage delivers to current task in headless or posts to webview when launched, and deleteQueuedMessage handles missing and existing task", async () => {
   const output = { appendLine: vi.fn() } as any
 
   const submitUserMessage = vi.fn().mockResolvedValue(undefined)
   const currentTask = { submitUserMessage } as any
 
   const provider: any = {
     viewLaunched: false,
     getCurrentTask: vi.fn(() => currentTask),
     postMessageToWebview: vi.fn(),
     context: {},
     on: vi.fn((ev: any, cb: any) => provider),
   }
 
   const api = new API(output, provider, undefined, true)
 
   // Headless path with a current task: should call submitUserMessage with empty string when text undefined
   await api.sendMessage()
   expect(submitUserMessage).toHaveBeenCalledTimes(1)
   expect(submitUserMessage).toHaveBeenCalledWith("", undefined)
 
   // Headless path with no current task: should log and not throw
   provider.getCurrentTask = vi.fn(() => undefined)
   output.appendLine.mockClear()
   await api.sendMessage("hello")
   // Should log a line mentioning no current task
   expect(output.appendLine.mock.calls.some((c: any[]) => String(c[0]).includes("no current task in headless mode; message dropped"))).toBe(true)
 
   // When viewLaunched true: should route via postMessageToWebview
   provider.viewLaunched = true
   provider.postMessageToWebview = vi.fn().mockResolvedValue(undefined)
   await api.sendMessage("hi", ["img1"])
   expect(provider.postMessageToWebview).toHaveBeenCalledWith({ type: "invoke", invoke: "sendMessage", text: "hi", images: ["img1"] })
 
   // deleteQueuedMessage: no current task -> logs and returns
   provider.getCurrentTask = vi.fn(() => undefined)
   output.appendLine.mockClear()
   api.deleteQueuedMessage("m-1")
   expect(output.appendLine.mock.calls.some((c: any[]) => String(c[0]).includes("no current task; ignoring delete for messageId m-1"))).toBe(true)
 
   // deleteQueuedMessage: current task with messageQueueService -> removeMessage should be called
   const removeMessage = vi.fn()
   const task = { messageQueueService: { removeMessage } }
   provider.getCurrentTask = vi.fn(() => task)
   api.deleteQueuedMessage("m-2")
   expect(removeMessage).toHaveBeenCalledWith("m-2")
 })


 it("profile management: create/update/upsert/delete/setActive flows and error cases", async () => {
   const output = { appendLine: vi.fn() } as any
 
   const provider: any = {
     context: {},
     on: vi.fn((ev: any, cb: any) => provider),
     // initial state: no profile entry exists
     getProviderProfileEntry: vi.fn(() => undefined),
     upsertProviderProfile: vi.fn().mockResolvedValue("upsert-id-1"),
     deleteProviderProfile: vi.fn().mockResolvedValue(undefined),
     getValues: vi.fn(() => ({ currentApiConfigName: "active-profile" })),
     activateProviderProfile: vi.fn().mockResolvedValue(undefined),
   }
 
   const api = new API(output, provider, undefined, false)
 
   // createProfile when no existing entry -> should call upsert and return id
   const id = await api.createProfile("new-profile", { apiKey: "x" }, true)
   expect(id).toBe("upsert-id-1")
   expect(provider.upsertProviderProfile).toHaveBeenCalledWith("new-profile", { apiKey: "x" }, true)
 
   // createProfile when entry already exists -> should throw
   provider.getProviderProfileEntry = vi.fn(() => ({ name: "new-profile" }))
   await expect(api.createProfile("new-profile")).rejects.toThrow(/already exists/)
 
   // updateProfile when entry missing -> throw
   provider.getProviderProfileEntry = vi.fn(() => undefined)
   await expect(api.updateProfile("missing", {})).rejects.toThrow(/does not exist/)
 
   // upsertProfile when upsert returns undefined -> throw
   provider.upsertProviderProfile = vi.fn().mockResolvedValue(undefined)
   await expect(api.upsertProfile("anything", {})).rejects.toThrow(/Failed to upsert profile/)
 
   // deleteProfile when entry missing -> throw
   provider.getProviderProfileEntry = vi.fn(() => undefined)
   await expect(api.deleteProfile("nope")).rejects.toThrow(/does not exist/)
 
   // setActiveProfile: with entry, should call activateProviderProfile and return active name
   provider.getProviderProfileEntry = vi.fn(() => ({ name: "p1" }))
   provider.getValues = vi.fn(() => ({ currentApiConfigName: "p1" }))
   const active = await api.setActiveProfile("p1")
   expect(provider.activateProviderProfile).toHaveBeenCalledWith({ name: "p1" })
   expect(active).toBe("p1")
 })


 it("waitForWebviewLaunch resolves true on immediate launch and false on timeout (with log)", async () => {
   const output = { appendLine: vi.fn() } as any
   const provider: any = { context: {}, on: vi.fn((ev: any, cb: any) => provider), viewLaunched: true }
   const api = new API(output, provider, undefined, true)
 
   // When viewLaunched is already true, should return true quickly
   provider.viewLaunched = true
   const ok = await (api as any).waitForWebviewLaunch(500)
   expect(ok).toBe(true)
 
   // When viewLaunched remains false, waitForWebviewLaunch should return false and log a message
   provider.viewLaunched = false
   // Use a short timeout so test runs quickly
   const result = await (api as any).waitForWebviewLaunch(50)
   expect(result).toBe(false)
   // Ensure a log line was written about the timeout
   expect(output.appendLine.mock.calls.some((c: any[]) => String(c[0]).includes("webview did not launch within"))).toBe(true)
 })


 it("outputChannelLog handles various arg types and non-serializable objects", () => {
   const output = { appendLine: vi.fn() } as any
   // minimal provider to satisfy registerListeners call in constructor
   const provider: any = { context: {}, on: vi.fn((ev: any, cb: any) => provider) }
   const api = new API(output, provider, undefined, true) // enable logging to exercise outputChannelLog path
 
   const circular: any = {}
   circular.self = circular
 
   // Call the private method via cast to any
   ;(api as any).outputChannelLog(
     null,
     undefined,
     "plain-string",
     new Error("boom"),
     { n: BigInt(42) },
     function anonymousFn() {},
     Symbol("sym"),
     circular,
   )
 
   const calls = output.appendLine.mock.calls.map((c: any[]) => String(c[0]))
 
   expect(calls).toContain("null")
   expect(calls).toContain("undefined")
   expect(calls).toContain("plain-string")
   expect(calls.some((c: string) => c.includes("Error: boom"))).toBe(true)
   // Combined serialization output should include BigInt and Function and Symbol representations
   expect(calls.join(" ")).toContain("BigInt(42)")
   expect(calls.join(" ")).toContain("Function:")
   expect(calls.join(" ")).toContain("Symbol(sym)")
   // Circular object should trigger the non-serializable fallback branch
   expect(calls.some((c: string) => c.includes("[Non-serializable object:"))).toBe(true)
 })

})
