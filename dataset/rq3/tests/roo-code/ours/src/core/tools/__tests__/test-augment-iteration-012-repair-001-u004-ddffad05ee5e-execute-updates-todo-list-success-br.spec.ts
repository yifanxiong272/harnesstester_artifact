import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("execute_updates_todo_list_success_branch_round_012", async () => {
  	const mod = await __testAugmentLoadTarget_8ba4bb791f97()
  	const { updateTodoListTool } = mod

  	const md = "[ ] Original task"

  	const pushToolResult = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	const handleError = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	const askApproval = __testAugmentVitest_a92c2c2279b8.vi.fn(() => Promise.resolve(true))

  	const task: any = {
  		consecutiveMistakeCount: 0,
  		recordToolError: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  		didToolFailInCurrentTurn: false,
  		say: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  	}

  	await updateTodoListTool.execute({ todos: md }, task, { pushToolResult, handleError, askApproval })

  	// Given the current implementation, approvedTodoList is cloned from normalizedTodos before approval
  	// so isTodoListChanged is false and the success message branch runs.
  	__testAugmentVitest_a92c2c2279b8.expect(pushToolResult).toHaveBeenCalled()
  	const firstArg = pushToolResult.mock.calls[0][0]
  	__testAugmentVitest_a92c2c2279b8.expect(String(firstArg)).toContain("Todo list updated successfully.")

  	// task.say should not be called because there is no detected user edit in this implementation
  	__testAugmentVitest_a92c2c2279b8.expect(task.say).not.toHaveBeenCalled()

  	// verify that the task.todoList was set and contains the parsed item
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toBeDefined()
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toHaveLength(1)
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList[0].content).toBe("Original task")
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList[0].status).toBe("pending")
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
