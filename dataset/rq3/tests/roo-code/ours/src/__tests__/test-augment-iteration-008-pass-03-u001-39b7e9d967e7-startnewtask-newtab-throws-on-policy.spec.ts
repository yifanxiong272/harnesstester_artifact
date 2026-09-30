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



  __testAugmentVitest_f6d4bbae43ca.it("startNewTask newTab throws when provider.createTask returns no task_round_008_pass_03", async () => {
  	// Mock openClineInNewTab before loading target so API uses it
  	__testAugmentVitest_f6d4bbae43ca.vi.doMock("../activate/registerCommands", () => ({
  		openClineInNewTab: __testAugmentVitest_f6d4bbae43ca.vi.fn(async () => providerStub),
  	}))
  	// Mock vscode.executeCommand used by startNewTask newTab branch
  	__testAugmentVitest_f6d4bbae43ca.vi.doMock("vscode", () => ({
  		commands: { executeCommand: __testAugmentVitest_f6d4bbae43ca.vi.fn(async () => undefined) },
  	}))

  	const output = { appendLine: __testAugmentVitest_f6d4bbae43ca.vi.fn() }
  	// provider that will be returned by openClineInNewTab
  	const providerStub = {
  		context: {},
  		on: __testAugmentVitest_f6d4bbae43ca.vi.fn(),
  		removeClineFromStack: __testAugmentVitest_f6d4bbae43ca.vi.fn(async () => undefined),
  		postStateToWebview: __testAugmentVitest_f6d4bbae43ca.vi.fn(async () => undefined),
  		postMessageToWebview: __testAugmentVitest_f6d4bbae43ca.vi.fn(async () => undefined),
  		createTask: __testAugmentVitest_f6d4bbae43ca.vi.fn(async () => undefined), // simulate policy rejection
  		getValues: () => ({}),
  	}

  	// Provide a sidebar provider instance used in constructor (won't be used for newTab path)
  	const initialProvider = { context: {}, on: __testAugmentVitest_f6d4bbae43ca.vi.fn(), getValues: () => ({}) }

  	const mod = await __testAugmentLoadTarget_6aaf15a5fb23()
  	const { API } = mod

  	const instance = new (API as any)(output, initialProvider as any, undefined, false)

  	// Now exercise the newTab=true path which should call openClineInNewTab and then throw when createTask returns falsy
  	await __testAugmentVitest_f6d4bbae43ca.expect(instance.startNewTask({ configuration: {}, text: "t", images: undefined, newTab: true })).rejects.toThrow("Failed to create task due to policy restrictions")

  	// ensure provider stub's createTask was invoked
  	__testAugmentVitest_f6d4bbae43ca.expect(providerStub.createTask).toHaveBeenCalled()
  })
})

import * as __testAugmentVitest_f6d4bbae43ca from "vitest";

const __testAugmentLoadTarget_6aaf15a5fb23 = async () => {
  __testAugmentVitest_f6d4bbae43ca.vi.doUnmock("../extension/api.js");
  __testAugmentVitest_f6d4bbae43ca.vi.resetModules();
  return import("../extension/api.js");
};
