import path from "path"

import type { MockedFunction } from "vitest"

import type { ToolUse } from "../../../shared/tools"
import { isPathOutsideWorkspace } from "../../../utils/pathUtils"
import type { Task } from "../../task/Task"
import { ApplyPatchTool } from "../ApplyPatchTool"
import * as fsUtils from "../../../utils/fs"
import * as applyPatchModule from "../apply-patch"

vi.mock("../../../utils/pathUtils", () => ({
	isPathOutsideWorkspace: vi.fn(),
}))

interface PartialApplyPatchPayload {
	tool: string
	path: string
	diff: string
	isOutsideWorkspace: boolean
}

function parsePartialApplyPatchPayload(payloadText: string): PartialApplyPatchPayload {
	const parsed: unknown = JSON.parse(payloadText)

	if (!parsed || typeof parsed !== "object") {
		throw new Error("Expected partial apply_patch payload to be a JSON object")
	}

	const payload = parsed as Record<string, unknown>

	return {
		tool: typeof payload.tool === "string" ? payload.tool : "",
		path: typeof payload.path === "string" ? payload.path : "",
		diff: typeof payload.diff === "string" ? payload.diff : "",
		isOutsideWorkspace: typeof payload.isOutsideWorkspace === "boolean" ? payload.isOutsideWorkspace : false,
	}
}

describe("ApplyPatchTool.handlePartial", () => {
	const cwd = path.join(path.sep, "workspace", "project")
	const mockedIsPathOutsideWorkspace = isPathOutsideWorkspace as MockedFunction<typeof isPathOutsideWorkspace>

	let askSpy: MockedFunction<Task["ask"]>
	let mockTask: Pick<Task, "cwd" | "ask">
	let tool: ApplyPatchTool

	beforeEach(() => {
		vi.clearAllMocks()

		askSpy = vi.fn().mockRejectedValue(new Error("ask() rejection is ignored for partial rows")) as MockedFunction<
			Task["ask"]
		>
		mockTask = {
			cwd,
			ask: askSpy,
		}

		mockedIsPathOutsideWorkspace.mockImplementation((absolutePath) =>
			absolutePath.replace(/\\/g, "/").includes("/outside/"),
		)
		tool = new ApplyPatchTool()
	})

	afterEach(() => {
		tool.resetPartialState()
	})

	function createPartialBlock(patchText?: string): ToolUse<"apply_patch"> {
		const params: ToolUse<"apply_patch">["params"] = {}
		if (patchText !== undefined) {
			params.patch = patchText
		}

		return {
			type: "tool_use",
			name: "apply_patch",
			params,
			partial: true,
		}
	}

	async function executePartial(patchText?: string): Promise<PartialApplyPatchPayload> {
		await tool.handlePartial(mockTask as Task, createPartialBlock(patchText))

		const call = askSpy.mock.calls.at(-1)
		expect(call).toBeDefined()

		if (!call) {
			throw new Error("Expected task.ask() to be called")
		}

		expect(call[0]).toBe("tool")
		expect(call[2]).toBe(true)

		const payloadText = call[1]
		expect(typeof payloadText).toBe("string")

		if (typeof payloadText !== "string") {
			throw new Error("Expected partial payload text to be a string")
		}

		return parsePartialApplyPatchPayload(payloadText)
	}

	it("emits non-empty path from the first complete file header", async () => {
		const patchText = `*** Begin Patch
*** Update File: src/first.ts
@@
-old
+new
*** End Patch`

		const payload = await executePartial(patchText)

		expect(payload.path).toBe("src/first.ts")
		expect(payload.path.length).toBeGreaterThan(0)
	})

	it("uses first header path deterministically for multi-file patches", async () => {
		const patchText = `*** Begin Patch
*** Add File: docs/first.md
+content
*** Update File: src/second.ts
@@
-a
+b
*** End Patch`

		const payload = await executePartial(patchText)

		expect(payload.path).toBe("docs/first.md")
	})

	it("keeps stable first path when trailing second header is truncated", async () => {
		/**
		 * The final line has no trailing newline on purpose, simulating streaming truncation.
		 * `extractFirstPathFromPatch()` should ignore this incomplete line and keep the first path.
		 */
		const patchText = `*** Begin Patch
*** Update File: src/stable-first.ts
@@
-old
+new
*** Update File: src/truncated-second`

		const payload = await executePartial(patchText)

		expect(payload.path).toBe("src/stable-first.ts")
		expect(payload.path).not.toBe("")
	})

	it("falls back to deterministic non-blank path when no header is present", async () => {
		const patchText = "*** Begin Patch\n@@\n-old\n+new"

		const firstPayload = await executePartial(patchText)
		const secondPayload = await executePartial(patchText)

		const expectedFallbackPath = path.basename(cwd)
		expect(firstPayload.path).toBe(expectedFallbackPath)
		expect(secondPayload.path).toBe(expectedFallbackPath)
		expect(firstPayload.path.length).toBeGreaterThan(0)
	})

	it("reflects isOutsideWorkspace for both derived and fallback paths", async () => {
		const derivedPatch = `*** Begin Patch
*** Update File: outside/derived.ts
@@
-old
+new
*** End Patch`
		const fallbackPatch = "*** Begin Patch\n@@\n-old\n+new"

		const derivedPayload = await executePartial(derivedPatch)
		const fallbackPayload = await executePartial(fallbackPatch)

		expect(derivedPayload.path).toBe("outside/derived.ts")
		expect(derivedPayload.isOutsideWorkspace).toBe(true)

		expect(fallbackPayload.path).toBe(path.basename(cwd))
		expect(fallbackPayload.isOutsideWorkspace).toBe(false)
	})

	it("preserves appliedDiff partial payload contract", async () => {
		const payload = await executePartial(undefined)

		expect(payload.tool).toBe("appliedDiff")
		expect(payload.diff).toBe("Parsing patch...")
		expect(payload.path).toBe(path.basename(cwd))
		expect(typeof payload.isOutsideWorkspace).toBe("boolean")
	})

 it("handle add file: existing file reports error", async () => {
   // Arrange: spy on fileExistsAtPath before creating the tool to ensure the live binding is mocked
   const fsUtils = await import("../../../utils/fs")
   const existsSpy = vi.spyOn(fsUtils, "fileExistsAtPath").mockResolvedValue(true)
 
   const tool = new ApplyPatchTool()
 
   const pushToolResult = vi.fn()
   const callbacks = {
     askApproval: vi.fn(),
     handleError: vi.fn(),
     pushToolResult,
   }
 
   const mockTask: any = {
     cwd: "/workspace/project",
     consecutiveMistakeCount: 0,
     recordToolError: vi.fn(),
     say: vi.fn(),
     // controllers not used for this branch but provided for shape
     rooIgnoreController: { validateAccess: () => true },
     rooProtectedController: { isWriteProtected: () => false },
     diffViewProvider: { reset: vi.fn() },
   }
 
   const change = {
     type: "add",
     path: "src/existing.ts",
     newContent: "hello",
   }
 
   // Act
   await (tool as any).handleAddFile(
     change,
     "/workspace/project/src/existing.ts",
     "src/existing.ts",
     mockTask,
     callbacks,
     false,
   )
 
   // Assert
   expect(mockTask.consecutiveMistakeCount).toBe(1)
   expect(mockTask.recordToolError).toHaveBeenCalledWith("apply_patch")
   expect(mockTask.say).toHaveBeenCalledWith("error", expect.stringContaining("src/existing.ts"))
   expect(pushToolResult).toHaveBeenCalled()
   // cleanup
   existsSpy.mockRestore()
 })


 it("processAllHunks failure records error and pushes tool error", async () => {
   const tool = new ApplyPatchTool()
   const applyPatchModule = await import("../apply-patch")
   // parsePatch returns a parsed patch with a hunk so processing is attempted
   const parseSpy = vi.spyOn(applyPatchModule, "parsePatch").mockImplementation(() => ({ hunks: [{}] }))
   const procSpy = vi.spyOn(applyPatchModule, "processAllHunks").mockImplementation(async () => {
     throw new Error("processing-failed")
   })
 
   const mockTask: Partial<Task> = {
     cwd: "/some/cwd",
     consecutiveMistakeCount: 0,
     recordToolError: vi.fn(),
   }
 
   const pushToolResult = vi.fn()
   const callbacks: any = {
     askApproval: vi.fn(),
     handleError: vi.fn(),
     pushToolResult,
   }
 
   await tool.execute({ patch: "*** Begin Patch\n@@\n-old\n+new\n" }, mockTask as unknown as Task, callbacks)
 
   expect(mockTask.consecutiveMistakeCount).toBe(1)
   expect(mockTask.recordToolError).toHaveBeenCalledWith("apply_patch")
   expect(pushToolResult).toHaveBeenCalled()
   expect(typeof pushToolResult.mock.calls[0][0]).toBe("string")
 
   parseSpy.mockRestore()
   procSpy.mockRestore()
   vi.restoreAllMocks()
 })


 it("parsed patch with no hunks pushes no operations message", async () => {
   const tool = new ApplyPatchTool()
   const applyPatchModule = await import("../apply-patch")
   const parseSpy = vi.spyOn(applyPatchModule, "parsePatch").mockImplementation(() => ({ hunks: [] }))
 
   const mockTask: Partial<Task> = {
     cwd: "/some/cwd",
     consecutiveMistakeCount: 0,
     recordToolError: vi.fn(),
   }
 
   const pushToolResult = vi.fn()
   const callbacks: any = {
     askApproval: vi.fn(),
     handleError: vi.fn(),
     pushToolResult,
   }
 
   await tool.execute({ patch: "*** Begin Patch\n*** End Patch\n" }, mockTask as unknown as Task, callbacks)
 
   expect(pushToolResult).toHaveBeenCalledWith("No file operations found in patch.")
 
   parseSpy.mockRestore()
   vi.restoreAllMocks()
 })


 it("parse_patch failure records error and pushes tool error", async () => {
   const tool = new ApplyPatchTool()
   // Import the module that exports parsePatch/ParseError so we can spy on it
   const applyPatchModule = await import("../apply-patch")
   const parseSpy = vi.spyOn(applyPatchModule, "parsePatch").mockImplementation(() => {
     // Throw the ParseError exported by the module to exercise the ParseError branch
     throw new applyPatchModule.ParseError("invalid-format")
   })
 
   const mockTask: Partial<Task> = {
     cwd: "/some/cwd",
     consecutiveMistakeCount: 0,
     recordToolError: vi.fn(),
   }
 
   const pushToolResult = vi.fn()
   const callbacks: any = {
     askApproval: vi.fn(),
     handleError: vi.fn(),
     pushToolResult,
   }
 
   await tool.execute({ patch: "irrelevant" }, mockTask as unknown as Task, callbacks)
 
   // Mistake count must have incremented and recordToolError called
   expect(mockTask.consecutiveMistakeCount).toBe(1)
   expect(mockTask.recordToolError).toHaveBeenCalledWith("apply_patch")
 
   // Should push some tool error string (formatting handled elsewhere)
   expect(pushToolResult).toHaveBeenCalled()
   expect(typeof pushToolResult.mock.calls[0][0]).toBe("string")
 
   parseSpy.mockRestore()
   vi.restoreAllMocks()
 })


 it("missing patch param increments mistake and pushes error", async () => {
   const tool = new ApplyPatchTool()
 
   // Minimal mock task to exercise the missing-parameter branch
   const mockTask: Partial<Task> = {
     cwd: "/some/cwd",
     consecutiveMistakeCount: 0,
     recordToolError: vi.fn(),
     sayAndCreateMissingParamError: vi.fn().mockResolvedValue("MISSING_PARAM_MESSAGE"),
   }
 
   const pushToolResult = vi.fn()
   const callbacks: ToolCallbacks = {
     askApproval: vi.fn() as any,
     handleError: vi.fn() as any,
     pushToolResult,
   }
 
   await tool.execute({}, mockTask as unknown as Task, callbacks)
 
   expect(mockTask.consecutiveMistakeCount).toBe(1)
   expect(mockTask.recordToolError).toHaveBeenCalledWith("apply_patch")
   expect(pushToolResult).toHaveBeenCalledTimes(1)
   expect(pushToolResult.mock.calls[0][0]).toBe("MISSING_PARAM_MESSAGE")
 })

})
