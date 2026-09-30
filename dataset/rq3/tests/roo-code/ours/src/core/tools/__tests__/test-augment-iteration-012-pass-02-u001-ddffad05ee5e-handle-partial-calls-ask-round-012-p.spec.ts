import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("handle_partial_calls_ask_round_012_pass_02", async () => {
  	const { updateTodoListTool } = await __testAugmentLoadTarget_8ba4bb791f97()

  	const ask = __testAugmentVitest_a92c2c2279b8.vi.fn(() => Promise.resolve())
  	const task: any = { ask }
  	const block: any = { params: { todos: "[x] Done" }, partial: "partial-token" }

  	await updateTodoListTool.handlePartial(task, block)

  	__testAugmentVitest_a92c2c2279b8.expect(ask).toHaveBeenCalledTimes(1)
  	const call = ask.mock.calls[0]
  	__testAugmentVitest_a92c2c2279b8.expect(call[0]).toBe("tool")

  	// approval message is JSON; verify shape and parsed todo content
  	const msg = JSON.parse(call[1])
  	__testAugmentVitest_a92c2c2279b8.expect(msg.tool).toBe("updateTodoList")
  	__testAugmentVitest_a92c2c2279b8.expect(Array.isArray(msg.todos)).toBe(true)
  	__testAugmentVitest_a92c2c2279b8.expect(msg.todos.length).toBeGreaterThanOrEqual(1)
  	__testAugmentVitest_a92c2c2279b8.expect(msg.todos[0].content).toBe("Done")
  	__testAugmentVitest_a92c2c2279b8.expect(call[2]).toBe("partial-token")
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
