import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("handle_partial_ask_rejection_handled_round_012_pass_02", async () => {
  	const { updateTodoListTool } = await __testAugmentLoadTarget_8ba4bb791f97()

  	const ask = __testAugmentVitest_a92c2c2279b8.vi.fn(() => Promise.reject(new Error("nope")))
  	const task: any = { ask }
  	const block: any = { params: { todos: "[ ] X" }, partial: "p" }

  	// The method should swallow rejections from task.ask and resolve
  	await __testAugmentVitest_a92c2c2279b8.expect(updateTodoListTool.handlePartial(task, block)).resolves.toBeUndefined()
  	__testAugmentVitest_a92c2c2279b8.expect(ask).toHaveBeenCalled()
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
