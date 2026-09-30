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



  __testAugmentVitest_f6d4bbae43ca.it("sendMessage drops message in headless mode when no current task_round_008", async () => {
  	const output = { appendLine: __testAugmentVitest_f6d4bbae43ca.vi.fn() }
  	const provider = {
  		viewLaunched: false,
  		getCurrentTask: __testAugmentVitest_f6d4bbae43ca.vi.fn(() => undefined),
  		postMessageToWebview: __testAugmentVitest_f6d4bbae43ca.vi.fn(),
  		on: __testAugmentVitest_f6d4bbae43ca.vi.fn(() => provider),
  		getValues: __testAugmentVitest_f6d4bbae43ca.vi.fn(() => ({})),
  		context: {},
  	}

  	const { API } = await __testAugmentLoadTarget_6aaf15a5fb23()
  	const api = new (API as any)(output, provider, undefined, true)

  	await api.sendMessage("hi there", ["img1.png"])

  	// In headless mode with no current task, postMessageToWebview is NOT called
  	__testAugmentVitest_f6d4bbae43ca.expect(provider.postMessageToWebview).toHaveBeenCalledTimes(0)

  	// And the logger should have been invoked with the drop message
  	const calls = (output.appendLine as any).mock.calls.map((c: any[]) => String(c[0]))
  	__testAugmentVitest_f6d4bbae43ca.expect(calls.some((s: string) => s.includes("[API#sendMessage] no current task in headless mode; message dropped"))).toBe(true)
  })
})

import * as __testAugmentVitest_f6d4bbae43ca from "vitest";

const __testAugmentLoadTarget_6aaf15a5fb23 = async () => {
  __testAugmentVitest_f6d4bbae43ca.vi.doUnmock("../extension/api.js");
  __testAugmentVitest_f6d4bbae43ca.vi.resetModules();
  return import("../extension/api.js");
};
