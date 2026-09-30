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



  __testAugmentVitest_f6d4bbae43ca.it("outputChannelLog handles various input types and serialization edge-cases_round_008", async () => {
  	// Load the target after constructing our lightweight provider that satisfies constructor expectations
  	const output = { appendLine: __testAugmentVitest_f6d4bbae43ca.vi.fn() }
  	const provider = {
  		on: __testAugmentVitest_f6d4bbae43ca.vi.fn(() => provider),
  		getValues: __testAugmentVitest_f6d4bbae43ca.vi.fn(() => ({})),
  		context: {},
  	}

  	const { API } = await __testAugmentLoadTarget_6aaf15a5fb23()
  	const api = new (API as any)(output, provider, undefined, true)

  	// Prepare variety of argument types
  	const circular: any = { a: 1 }
  	circular.self = circular

  	// Call the runtime log function which delegates to outputChannelLog
  	;(api as any).log(
  		null,
  		undefined,
  		"a simple string",
  		new Error("boom"),
  		{ someBig: BigInt(123) },
  		function namedFn() {},
  		Symbol("mysym"),
  		circular,
  	)

  	// assert appendLine was invoked for the different branches
  	const calls = (output.appendLine as any).mock.calls.map((c: any[]) => String(c[0]))

  	// null and undefined branches
  	__testAugmentVitest_f6d4bbae43ca.expect(calls).toEqual(expect.arrayContaining(["null", "undefined"]))

  	// string and error formatting
  	__testAugmentVitest_f6d4bbae43ca.expect(calls.some((s: string) => s.includes("a simple string"))).toBe(true)
  	__testAugmentVitest_f6d4bbae43ca.expect(calls.some((s: string) => s.includes("Error: boom"))).toBe(true)

  	// BigInt should be rendered via replacer
  	__testAugmentVitest_f6d4bbae43ca.expect(calls.some((s: string) => s.includes("BigInt(123)"))).toBe(true)

  	// function and symbol should be converted to readable forms
  	__testAugmentVitest_f6d4bbae43ca.expect(calls.some((s: string) => s.includes("Function: namedFn"))).toBe(true)
  	__testAugmentVitest_f6d4bbae43ca.expect(calls.some((s: string) => s.includes("Symbol(mysym)"))).toBe(true)

  	// circular should trigger non-serializable catch branch
  	__testAugmentVitest_f6d4bbae43ca.expect(calls.some((s: string) => s.includes("Non-serializable object"))).toBe(true)
  })
})

import * as __testAugmentVitest_f6d4bbae43ca from "vitest";

const __testAugmentLoadTarget_6aaf15a5fb23 = async () => {
  __testAugmentVitest_f6d4bbae43ca.vi.doUnmock("../extension/api.js");
  __testAugmentVitest_f6d4bbae43ca.vi.resetModules();
  return import("../extension/api.js");
};
