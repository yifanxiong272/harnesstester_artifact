import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("execute_decline_branch_round_012_pass_03", async () => {
  	const { updateTodoListTool } = await __testAugmentLoadTarget_8ba4bb791f97()

  	const pushToolResult = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	const handleError = __testAugmentVitest_a92c2c2279b8.vi.fn()
  	// user declines approval
  	const askApproval = __testAugmentVitest_a92c2c2279b8.vi.fn(() => Promise.resolve(false))

  	const task: any = {
  		consecutiveMistakeCount: 0,
  		recordToolError: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  		didToolFailInCurrentTurn: false,
  		say: __testAugmentVitest_a92c2c2279b8.vi.fn(),
  	}

  	await updateTodoListTool.execute({ todos: "[ ] Keep this" }, task, { pushToolResult, handleError, askApproval })

  	// When askApproval resolves to false, the tool should push the decline message and not set the todoList
  	__testAugmentVitest_a92c2c2279b8.expect(pushToolResult).toHaveBeenCalled()
  	const arg = pushToolResult.mock.calls[0][0]
  	__testAugmentVitest_a92c2c2279b8.expect(String(arg)).toBe("User declined to update the todoList.")
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toBeUndefined()
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
