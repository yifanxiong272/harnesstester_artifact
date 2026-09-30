import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("handle_partial_handles_non_string_round_012_pass_02", async () => {
  	const { updateTodoListTool } = await __testAugmentLoadTarget_8ba4bb791f97()

  	const ask = __testAugmentVitest_a92c2c2279b8.vi.fn(() => Promise.resolve())
  	const task: any = { ask }
  	// Provide undefined todos to hit the 'todosRaw || ""' path that results in an empty parsed list
  	const block: any = { params: { todos: undefined }, partial: "p" }

  	await updateTodoListTool.handlePartial(task, block)

  	__testAugmentVitest_a92c2c2279b8.expect(ask).toHaveBeenCalled()
  	const call = ask.mock.calls[0]
  	const msg = JSON.parse(call[1])
  	__testAugmentVitest_a92c2c2279b8.expect(Array.isArray(msg.todos)).toBe(true)
  	__testAugmentVitest_a92c2c2279b8.expect(msg.todos).toHaveLength(0)
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
