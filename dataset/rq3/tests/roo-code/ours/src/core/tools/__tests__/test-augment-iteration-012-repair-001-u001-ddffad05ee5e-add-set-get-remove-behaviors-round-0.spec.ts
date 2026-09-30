import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"

describe("parseMarkdownChecklist", () => {




  __testAugmentVitest_a92c2c2279b8.it("add_set_get_remove behaviors_round_012", async () => {
  	const { addTodoToTask, getTodoListForTask, setTodoListForTask, removeTodoFromTask } = await __testAugmentLoadTarget_8ba4bb791f97()

  	const task: any = {}

  	// add with explicit id is deterministic
  	const todo = addTodoToTask(task, "Write tests", "pending", "id-1")
  	__testAugmentVitest_a92c2c2279b8.expect(todo.id).toBe("id-1")
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toHaveLength(1)

  	// get returns a shallow copy
  	const list = getTodoListForTask(task)
  	__testAugmentVitest_a92c2c2279b8.expect(list).toHaveLength(1)
  	__testAugmentVitest_a92c2c2279b8.expect(list).not.toBe(task.todoList)
  	// mutating returned copy should not change original
  	list.push({ id: "x", content: "x", status: "pending" })
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toHaveLength(1)

  	// setTodoListForTask tolerates undefined cline and undefined todos
  	setTodoListForTask(undefined, [])
  	setTodoListForTask(task, undefined)
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toEqual([])

  	// remove missing id returns false
  	__testAugmentVitest_a92c2c2279b8.expect(removeTodoFromTask(task, "nope")).toBe(false)

  	// add and remove works
  	addTodoToTask(task, "Remove me", "pending", "rem-id")
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toHaveLength(1)
  	__testAugmentVitest_a92c2c2279b8.expect(removeTodoFromTask(task, "rem-id")).toBe(true)
  	__testAugmentVitest_a92c2c2279b8.expect(task.todoList).toHaveLength(0)
  })
})

import * as __testAugmentVitest_a92c2c2279b8 from "vitest";

const __testAugmentLoadTarget_8ba4bb791f97 = async () => {
  __testAugmentVitest_a92c2c2279b8.vi.doUnmock("../UpdateTodoListTool.js");
  __testAugmentVitest_a92c2c2279b8.vi.resetModules();
  return import("../UpdateTodoListTool.js");
};
