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



  __testAugmentVitest_f6d4bbae43ca.it("ipc GetCommands error results in CommandsResponse with empty array_round_008_pass_02", async () => {
  	// Mock IpcServer so we capture send() calls
  	__testAugmentVitest_f6d4bbae43ca.vi.doMock("@roo-code/ipc", () => {
  		return {
  			IpcServer: class MockIpc {
  				constructor() {
  					this.listen = __testAugmentVitest_f6d4bbae43ca.vi.fn()
  					this.send = __testAugmentVitest_f6d4bbae43ca.vi.fn()
  				}
  				on(type: any, cb: any) {
  					this._cb = cb
  				}
  			}
  		}
  	})

  	// Mock the commands fetcher to throw to exercise the error path -> sendResponse(..., [[]])
  	__testAugmentVitest_f6d4bbae43ca.vi.doMock("../services/command/commands", () => ({
  		getCommands: __testAugmentVitest_f6d4bbae43ca.vi.fn(async () => { throw new Error("command fetch failed") }),
  	}))

  	const types = await import("@roo-code/types")
  	const output = { appendLine: __testAugmentVitest_f6d4bbae43ca.vi.fn() }
  	const provider = { getValues: () => ({}), on: __testAugmentVitest_f6d4bbae43ca.vi.fn(), context: {} }

  	const mod = await __testAugmentLoadTarget_6aaf15a5fb23()
  	const { API } = mod

  	const instance = new (API as any)(output, provider, "/tmp/ipc2.sock", false)
  	const ipc = (instance as any).ipc

  	// trigger GetCommands command
  	const cmd = { commandName: types.TaskCommandName.GetCommands, data: {} }
  	await ipc._cb("client-x", cmd)

  	// ipc.send should have been used to send the CommandsResponse
  	__testAugmentVitest_f6d4bbae43ca.expect(ipc.send).toHaveBeenCalled()
  	const sent = (ipc.send as any).mock.calls[0][1]
  	__testAugmentVitest_f6d4bbae43ca.expect(sent.type).toBe(types.IpcMessageType.TaskEvent)
  	__testAugmentVitest_f6d4bbae43ca.expect(sent.origin).toBe(types.IpcOrigin.Server)
  	__testAugmentVitest_f6d4bbae43ca.expect(sent.data.eventName).toBe(types.RooCodeEventName.CommandsResponse)
  	// payload should be an array whose first element is an empty array as the catch branch sends
  	__testAugmentVitest_f6d4bbae43ca.expect(Array.isArray(sent.data.payload)).toBe(true)
  	__testAugmentVitest_f6d4bbae43ca.expect(Array.isArray(sent.data.payload[0])).toBe(true)
  	__testAugmentVitest_f6d4bbae43ca.expect(sent.data.payload[0].length).toBe(0)
  })
})

import * as __testAugmentVitest_f6d4bbae43ca from "vitest";

const __testAugmentLoadTarget_6aaf15a5fb23 = async () => {
  __testAugmentVitest_f6d4bbae43ca.vi.doUnmock("../extension/api.js");
  __testAugmentVitest_f6d4bbae43ca.vi.resetModules();
  return import("../extension/api.js");
};
