import { describe, it, expect, beforeEach, vi } from "vitest"
import { parseMarkdownChecklist } from "../UpdateTodoListTool"
import { TodoItem } from "@roo-code/types"
import * as U from "../UpdateTodoListTool"
import { setPendingTodoList, updateTodoListTool } from "../UpdateTodoListTool"
import { removeTodoFromTask } from "../UpdateTodoListTool"
import { updateTodoStatusForTask } from "../UpdateTodoListTool"
import { addTodoToTask, getTodoListForTask, setTodoListForTask, restoreTodoListForTask } from "../UpdateTodoListTool"

describe("parseMarkdownChecklist", () => {
	describe("standard checkbox format (without dash prefix)", () => {
		it("should parse pending tasks", () => {
			const md = `[ ] Task 1
[ ] Task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("Task 1")
			expect(result[0].status).toBe("pending")
			expect(result[1].content).toBe("Task 2")
			expect(result[1].status).toBe("pending")
		})

		it("should parse completed tasks with lowercase x", () => {
			const md = `[x] Completed task 1
[x] Completed task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("Completed task 1")
			expect(result[0].status).toBe("completed")
			expect(result[1].content).toBe("Completed task 2")
			expect(result[1].status).toBe("completed")
		})

		it("should parse completed tasks with uppercase X", () => {
			const md = `[X] Completed task 1
[X] Completed task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("Completed task 1")
			expect(result[0].status).toBe("completed")
			expect(result[1].content).toBe("Completed task 2")
			expect(result[1].status).toBe("completed")
		})

		it("should parse in-progress tasks with dash", () => {
			const md = `[-] In progress task 1
[-] In progress task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("In progress task 1")
			expect(result[0].status).toBe("in_progress")
			expect(result[1].content).toBe("In progress task 2")
			expect(result[1].status).toBe("in_progress")
		})

		it("should parse in-progress tasks with tilde", () => {
			const md = `[~] In progress task 1
[~] In progress task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("In progress task 1")
			expect(result[0].status).toBe("in_progress")
			expect(result[1].content).toBe("In progress task 2")
			expect(result[1].status).toBe("in_progress")
		})
	})

	describe("dash-prefixed checkbox format", () => {
		it("should parse pending tasks with dash prefix", () => {
			const md = `- [ ] Task 1
- [ ] Task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("Task 1")
			expect(result[0].status).toBe("pending")
			expect(result[1].content).toBe("Task 2")
			expect(result[1].status).toBe("pending")
		})

		it("should parse completed tasks with dash prefix and lowercase x", () => {
			const md = `- [x] Completed task 1
- [x] Completed task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("Completed task 1")
			expect(result[0].status).toBe("completed")
			expect(result[1].content).toBe("Completed task 2")
			expect(result[1].status).toBe("completed")
		})

		it("should parse completed tasks with dash prefix and uppercase X", () => {
			const md = `- [X] Completed task 1
- [X] Completed task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("Completed task 1")
			expect(result[0].status).toBe("completed")
			expect(result[1].content).toBe("Completed task 2")
			expect(result[1].status).toBe("completed")
		})

		it("should parse in-progress tasks with dash prefix and dash marker", () => {
			const md = `- [-] In progress task 1
- [-] In progress task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("In progress task 1")
			expect(result[0].status).toBe("in_progress")
			expect(result[1].content).toBe("In progress task 2")
			expect(result[1].status).toBe("in_progress")
		})

		it("should parse in-progress tasks with dash prefix and tilde marker", () => {
			const md = `- [~] In progress task 1
- [~] In progress task 2`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("In progress task 1")
			expect(result[0].status).toBe("in_progress")
			expect(result[1].content).toBe("In progress task 2")
			expect(result[1].status).toBe("in_progress")
		})
	})

	describe("mixed formats", () => {
		it("should parse mixed formats correctly", () => {
			const md = `[ ] Task without dash
- [ ] Task with dash
[x] Completed without dash
- [X] Completed with dash
[-] In progress without dash
- [~] In progress with dash`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(6)

			expect(result[0].content).toBe("Task without dash")
			expect(result[0].status).toBe("pending")

			expect(result[1].content).toBe("Task with dash")
			expect(result[1].status).toBe("pending")

			expect(result[2].content).toBe("Completed without dash")
			expect(result[2].status).toBe("completed")

			expect(result[3].content).toBe("Completed with dash")
			expect(result[3].status).toBe("completed")

			expect(result[4].content).toBe("In progress without dash")
			expect(result[4].status).toBe("in_progress")

			expect(result[5].content).toBe("In progress with dash")
			expect(result[5].status).toBe("in_progress")
		})
	})

	describe("edge cases", () => {
		it("should handle empty strings", () => {
			const result = parseMarkdownChecklist("")
			expect(result).toEqual([])
		})

		it("should handle non-string input", () => {
			const result = parseMarkdownChecklist(null as any)
			expect(result).toEqual([])
		})

		it("should handle undefined input", () => {
			const result = parseMarkdownChecklist(undefined as any)
			expect(result).toEqual([])
		})

		it("should ignore non-checklist lines", () => {
			const md = `This is not a checklist
[ ] Valid task
Just some text
- Not a checklist item
- [x] Valid completed task
[not valid] Invalid format`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(2)
			expect(result[0].content).toBe("Valid task")
			expect(result[0].status).toBe("pending")
			expect(result[1].content).toBe("Valid completed task")
			expect(result[1].status).toBe("completed")
		})

		it("should handle extra spaces", () => {
			const md = `  [ ]   Task with spaces  
-  [ ]  Task with dash and spaces
  [x]  Completed with spaces
-   [X]   Completed with dash and spaces`
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(4)
			expect(result[0].content).toBe("Task with spaces")
			expect(result[1].content).toBe("Task with dash and spaces")
			expect(result[2].content).toBe("Completed with spaces")
			expect(result[3].content).toBe("Completed with dash and spaces")
		})

		it("should handle Windows line endings", () => {
			const md = "[ ] Task 1\r\n- [x] Task 2\r\n[-] Task 3"
			const result = parseMarkdownChecklist(md)
			expect(result).toHaveLength(3)
			expect(result[0].content).toBe("Task 1")
			expect(result[0].status).toBe("pending")
			expect(result[1].content).toBe("Task 2")
			expect(result[1].status).toBe("completed")
			expect(result[2].content).toBe("Task 3")
			expect(result[2].status).toBe("in_progress")
		})
	})

	describe("ID generation", () => {
		it("should generate consistent IDs for the same content and status", () => {
			const md1 = `[ ] Task 1
[x] Task 2`
			const md2 = `[ ] Task 1
[x] Task 2`
			const result1 = parseMarkdownChecklist(md1)
			const result2 = parseMarkdownChecklist(md2)

			expect(result1[0].id).toBe(result2[0].id)
			expect(result1[1].id).toBe(result2[1].id)
		})

		it("should generate different IDs for different content", () => {
			const md = `[ ] Task 1
[ ] Task 2`
			const result = parseMarkdownChecklist(md)
			expect(result[0].id).not.toBe(result[1].id)
		})

		it("should generate different IDs for same content but different status", () => {
			const md = `[ ] Task 1
[x] Task 1`
			const result = parseMarkdownChecklist(md)
			expect(result[0].id).not.toBe(result[1].id)
		})

		it("should generate same IDs regardless of dash prefix", () => {
			const md1 = `[ ] Task 1`
			const md2 = `- [ ] Task 1`
			const result1 = parseMarkdownChecklist(md1)
			const result2 = parseMarkdownChecklist(md2)
			expect(result1[0].id).toBe(result2[0].id)
		})

  it("execute handles user-edited approvedTodoList and emits User edits todo result", async () => {
    const U = await import("../UpdateTodoListTool")
    const tool = new U.UpdateTodoListTool()
    // Start with a simple pending todo in markdown
    const md = `[ ] Task A`
    const task: any = {
      consecutiveMistakeCount: 0,
      recordToolError: vi.fn(),
      didToolFailInCurrentTurn: false,
      say: vi.fn(),
      clineMessages: [],
      todoList: undefined,
    }
    const pushToolResult = vi.fn()
    const handleError = vi.fn()
    // askApproval will modify the globally-approved list to a changed list (in_progress)
    const askApproval = vi.fn(async () => {
      // Set approvedTodoList to a different version (in_progress) while approval is happening
      U.setPendingTodoList([{ id: "changed-id", content: "Task A", status: "in_progress" }])
      return true
    })
    const callbacks = { pushToolResult, handleError, askApproval }
    // Act
    await tool.execute({ todos: md }, task, callbacks as any)
    // Assert
    // task.say should be called to notify of user edits
    expect(task.say).toHaveBeenCalledWith(
      "user_edit_todos",
      JSON.stringify({
        tool: "updateTodoList",
        todos: [{ id: "changed-id", content: "Task A", status: "in_progress" }],
      }),
    )
    // pushToolResult should include the User edits todo text and the in-progress marker "[-]"
    const pushed = pushToolResult.mock.calls[0][0] as string
    expect(pushed).toContain("User edits todo:")
    expect(pushed).toContain("[-] Task A")
    // The task.todoList should have been set to the approved (changed) list
    expect(task.todoList).toEqual([{ id: "changed-id", content: "Task A", status: "in_progress" }])
  })


  it("should handle approval edits and handlePartial sends approval message", async () => {
    const md = `- [ ] Task A`
  
    const task: any = {
      consecutiveMistakeCount: 0,
      recordToolError: vi.fn(),
      didToolFailInCurrentTurn: false,
      say: vi.fn(),
      clineMessages: [],
      todoList: undefined,
      ask: vi.fn().mockResolvedValue(undefined),
    }
  
    const pushToolResult = vi.fn()
    const handleError = vi.fn()
  
    // askApproval will simulate user editing the todo list by calling setPendingTodoList
    const askApproval = vi.fn().mockImplementation(async (_type: string, _msg: string) => {
      // Simulate the user editing the list: replace with a completed edited todo
      setPendingTodoList([
        { id: "edited-1", content: "Edited task", status: "completed" },
      ])
      return true
    })
  
    await updateTodoListTool.execute({ todos: md }, task, { pushToolResult, handleError, askApproval })
  
    // Because the mock askApproval replaced the approved todo list, the tool should detect change,
    // call task.say and update the task.todoList to the approved (edited) list
    expect(task.say).toHaveBeenCalled()
    expect(task.todoList).toBeDefined()
    expect(task.todoList).toHaveLength(1)
    expect(task.todoList[0].content).toBe("Edited task")
  
    // pushToolResult should have been called at least once (for the user edits result)
    expect(pushToolResult).toHaveBeenCalled()
  
    // Test handlePartial: it should call task.ask with tool approval message containing parsed todos
    const block: any = { params: { todos: md }, partial: "partial-data" }
    await updateTodoListTool.handlePartial(task, block)
    expect(task.ask).toHaveBeenCalled()
    const askArgs = task.ask.mock.calls[0]
    expect(askArgs[0]).toBe("tool")
    // The second arg should be a JSON string that, when parsed, contains the todos array
    const parsed = JSON.parse(askArgs[1])
    expect(parsed.tool).toBe("updateTodoList")
    expect(Array.isArray(parsed.todos)).toBe(true)
  })


  it("should remove todo items and return false for missing or absent lists", () => {
    const task: any = {
      todoList: [
        { id: "r1", content: "Remove me", status: "pending" },
        { id: "r2", content: "Keep me", status: "pending" },
      ],
    }
  
    // remove existing
    expect(removeTodoFromTask(task, "r1")).toBe(true)
    expect(task.todoList).toHaveLength(1)
    expect(task.todoList[0].id).toBe("r2")
  
    // remove non-existent
    expect(removeTodoFromTask(task, "non-existent")).toBe(false)
  
    // no todoList on task
    expect(removeTodoFromTask({} as any, "r2")).toBe(false)
  })


  it("should update todo statuses for valid transitions and reject invalid ones", () => {
    const task: any = {
      todoList: [
        { id: "t1", content: "Task 1", status: "pending" },
        { id: "t2", content: "Task 2", status: "in_progress" },
      ],
    }
  
    // pending -> in_progress is allowed
    expect(updateTodoStatusForTask(task, "t1", "in_progress")).toBe(true)
    expect(task.todoList.find((t: any) => t.id === "t1")!.status).toBe("in_progress")
  
    // in_progress -> completed is allowed
    expect(updateTodoStatusForTask(task, "t1", "completed")).toBe(true)
    expect(task.todoList.find((t: any) => t.id === "t1")!.status).toBe("completed")
  
    // in_progress -> pending is not allowed (for t2)
    expect(updateTodoStatusForTask(task, "t2", "pending")).toBe(false)
    expect(task.todoList.find((t: any) => t.id === "t2")!.status).toBe("in_progress")
  
    // Non-existent list returns false
    expect(updateTodoStatusForTask({} as any, "no", "pending")).toBe(false)
  })


  it("should add a todo, return a copy, set and restore todo list correctly", async () => {
    const task: any = {}
    // Add a todo with a deterministic id
    const todo = addTodoToTask(task, "My deterministic task", "pending", "det-id-1")
    expect(todo).toBeDefined()
    expect(todo.id).toBe("det-id-1")
    expect(task.todoList).toHaveLength(1)
    expect(task.todoList[0].content).toBe("My deterministic task")
  
    // getTodoListForTask returns a copy (modifying it should not change original)
    const copy = getTodoListForTask(task)
    expect(copy).not.toBe(task.todoList)
    copy.push({ id: "x", content: "x", status: "pending" })
    expect(task.todoList).toHaveLength(1)
  
    // setTodoListForTask with undefined cline should be a no-op and not throw
    await setTodoListForTask(undefined, [{ id: "a", content: "A", status: "pending" }])
  
    // setTodoListForTask with undefined todos should set an empty list
    await setTodoListForTask(task, undefined)
    expect(task.todoList).toEqual([])
  
    // restoreTodoListForTask with an explicit list should set it
    restoreTodoListForTask(task, [{ id: "r1", content: "Restored", status: "completed" }])
    expect(task.todoList).toHaveLength(1)
    expect(task.todoList[0].content).toBe("Restored")
    expect(task.todoList[0].status).toBe("completed")
  })

	})
})
