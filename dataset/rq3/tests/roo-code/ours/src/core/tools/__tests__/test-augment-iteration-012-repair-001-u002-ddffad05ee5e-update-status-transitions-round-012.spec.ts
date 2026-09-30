import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("update_status_transitions_round_012", async () => {
  	const { updateTodoStatusForTask } = await __testAugmentLoadTarget_8ba4bb791f97()

  	const task: any = {
  		todoList: [
  			{ id: "a", content: "A", status: "pending" },
  			{ id: "b", content: "B", status: "in_progress" },
  			{ id: "c", content: "C", status: "completed" },
  		],
  	}

  	// pending -> in_progress allowed
  	__testAugmentVitest_a92c2c2279b8.expect(updateTodoStatusForTask(task, "a", "in_progress")).toBe(true)
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList.find((t: any) => t.id === "a")!.status).toBe("in_progress")

  	// in_progress -> completed allowed
  	__testAugmentVitest_a92c2c2279b8.expect(updateTodoStatusForTask(task, "b", "completed")).toBe(true)

  	// in_progress -> completed for 'a' (which was promoted) is allowed
  	__testAugmentVitest_a92c2c2279b8.expect(updateTodoStatusForTask(task, "a", "completed")).toBe(true)

  	// invalid direct transition pending -> completed should be rejected
  	const task2: any = { todoList: [{ id: "d", content: "D", status: "pending" }] }
  	__testAugmentVitest_a92c2c2279b8.expect(updateTodoStatusForTask(task2, "d", "completed")).toBe(false)

  	// same status should return true
  	__testAugmentVitest_a92c2c2279b8.expect(updateTodoStatusForTask(task, "c", "completed")).toBe(true)

  	// missing todoList or missing id returns false
  	__testAugmentVitest_a92c2c2279b8.expect(updateTodoStatusForTask({} as any, "x", "pending")).toBe(false)
  	__testAugmentVitest_a92c2c2279b8.expect(updateTodoStatusForTask({ todoList: [] } as any, "x", "pending")).toBe(false)
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
