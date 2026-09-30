import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("set_pending_then_execute_round_012_pass_03", async () => {
  	const mod = await __testAugmentLoadTarget_8ba4bb791f97()
  	const { setPendingTodoList, updateTodoListTool } = mod

  	// Prime module-level approvedTodoList (not directly observable) — this should not throw
  	setPendingTodoList([{ id: "p1", content: "Primed", status: "pending" }])

  	const pushToolResult = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	const handleError = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	const askApproval = __testAugmentVitest_a92c2c2279b8.vi.fn(() => Promise.resolve(true))

  	const task: any = {
  		consecutiveMistakeCount: 0,
  		recordToolError: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  		didToolFailInCurrentTurn: false,
  		say: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  	}

  	await updateTodoListTool.execute({ todos: "[ ] New task" }, task, { pushToolResult, handleError, askApproval })

  	// Should still complete normal flow (success message) and set the task.todoList
  	__testAugmentVitest_a92c2c2279b8.expect(pushToolResult).toHaveBeenCalled()
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toBeDefined()
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList[0].content).toBe("New task")
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
