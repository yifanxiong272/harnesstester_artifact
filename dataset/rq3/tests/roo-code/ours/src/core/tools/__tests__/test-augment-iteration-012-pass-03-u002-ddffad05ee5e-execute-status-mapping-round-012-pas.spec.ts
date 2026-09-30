import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("execute_status_mapping_round_012_pass_03", async () => {
  	const { updateTodoListTool } = await __testAugmentLoadTarget_8ba4bb791f97()

  	const pushToolResult = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	const handleError = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	const askApproval = __testAugmentVitest_a92c2c2279b8.vi.fn(() => Promise.resolve(true))

  	// Mix of completed, in_progress and pending markers
  	const md = `[x] Done task\n[-] Doing task\n[ ] Todo task`

  	const task: any = {
  		consecutiveMistakeCount: 0,
  		recordToolError: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  		didToolFailInCurrentTurn: false,
  		say: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  	}

  	await updateTodoListTool.execute({ todos: md }, task, { pushToolResult, handleError, askApproval })

  	// Normal flow: success message pushed
  	__testAugmentVitest_a92c2c2279b8.expect(pushToolResult).toHaveBeenCalled()

  	// Verify normalized statuses were applied to task.todoList
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toBeDefined()
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toHaveLength(3)
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList[0].status).toBe("completed")
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList[1].status).toBe("in_progress")
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList[2].status).toBe("pending")
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
