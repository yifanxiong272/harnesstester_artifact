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



  __testAugmentVitest_f6d4bbae43ca.it("emit broadcasts via ipc and invokes registered listeners_round_008_pass_03", async () => {
  	const output = { appendLine: __testAugmentVitest_f6d4bbae43ca.vi.fn() }
  	const provider = { context: {}, on: __testAugmentVitest_f6d4bbae43ca.vi.fn(), getValues: () => ({}) }

  	const mod = await __testAugmentLoadTarget_6aaf15a5fb23()
  	const { API } = mod

  	const instance = new (API as any)(output, provider as any, undefined, false)

  	// attach listener to observe super.emit behavior
  	const listener = __testAugmentVitest_f6d4bbae43ca.vi.fn()
  	instance.on("TaskStarted", listener)

  	// inject an ipc with broadcast spy
  	const fakeIpc = { broadcast: __testAugmentVitest_f6d4bbae43ca.vi.fn() }
  	;(instance as any).ipc = fakeIpc

  	// call emit; API.emit should call ipc.broadcast and then call listener
  	instance.emit("TaskStarted", "task-xyz")

  	__testAugmentVitest_f6d4bbae43ca.expect(fakeIpc.broadcast).toHaveBeenCalled()
  	const broadcastArg = (fakeIpc.broadcast as any).mock.calls[0][0]
  	__testAugmentVitest_f6d4bbae43ca.expect(broadcastArg.type).toBe((await import("@roo-code/types")).IpcMessageType.TaskEvent)

  	__testAugmentVitest_f6d4bbae43ca.expect(listener).toHaveBeenCalledWith("task-xyz")
  })
})

import * as __testAugmentVitest_f6d4bbae43ca from "vitest";

const __testAugmentLoadTarget_6aaf15a5fb23 = async () => {
  __testAugmentVitest_f6d4bbae43ca.vi.doUnmock("../extension/api.js");
  __testAugmentVitest_f6d4bbae43ca.vi.resetModules();
  return import("../extension/api.js");
};
