// npx vitest run src/services/checkpoints/__tests__/ShadowCheckpointService.spec.ts

import fs from "fs/promises"
import path from "path"
import os from "os"
import { EventEmitter } from "events"

import { simpleGit, SimpleGit } from "simple-git"

import { fileExistsAtPath } from "../../../utils/fs"
import * as fileSearch from "../../../services/search/file-search"

import { RepoPerTaskCheckpointService } from "../RepoPerTaskCheckpointService"

const tmpDir = path.join(os.tmpdir(), "CheckpointService")

const initWorkspaceRepo = async ({
	workspaceDir,
	userName = "Roo Code",
	userEmail = "support@roocode.com",
	testFileName = "test.txt",
	textFileContent = "Hello, world!",
}: {
	workspaceDir: string
	userName?: string
	userEmail?: string
	testFileName?: string
	textFileContent?: string
}) => {
	// Create a temporary directory for testing.
	await fs.mkdir(workspaceDir, { recursive: true })

	// Initialize git repo.
	const git = simpleGit(workspaceDir)
	await git.init()
	await git.addConfig("user.name", userName)
	await git.addConfig("user.email", userEmail)

	// Create test file.
	const testFile = path.join(workspaceDir, testFileName)
	await fs.writeFile(testFile, textFileContent)

	// Create initial commit.
	await git.add(".")
	await git.commit("Initial commit")!

	return { git, testFile }
}


describe("worktree path comparison", () => {

  __testAugmentVitest_83160e95320a.test("saveCheckpoint_no_git_emits_error_round_025_pass_02", async () => {
  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	class Concrete extends ShadowCheckpointService {}

  	const logs: string[] = []
  	const service = new Concrete("task-id-2", "/tmp/checkpoints-y", "/tmp/workspace-y", (m: string) => logs.push(m))

  	// Attach an error listener to verify the error event is emitted when saveCheckpoint fails.
  	const handler = __testAugmentVitest_83160e95320a.vi.fn()
  	service.on("error", handler)

  	// Calling saveCheckpoint without an initialized git should reject and emit an error event.
  	await __testAugmentVitest_83160e95320a.expect(service.saveCheckpoint("msg")).rejects.toThrowError(
  		/Shadow git repo not initialized/,
  	)

  	// The error handler should have been called once with an object containing the Error.
  	__testAugmentVitest_83160e95320a.expect(handler).toHaveBeenCalled()
  	const calledWith = handler.mock.calls[0][0]
  	__testAugmentVitest_83160e95320a.expect(calledWith).toHaveProperty("type", "error")
  	__testAugmentVitest_83160e95320a.expect(calledWith).toHaveProperty("error")
  	__testAugmentVitest_83160e95320a.expect(calledWith.error).toBeInstanceOf(Error)

  	// Also assert the service logged the starting message (sanity check for the try-block entry).
  	__testAugmentVitest_83160e95320a.expect(logs.some((l) => l.includes("starting checkpoint save"))).toBe(true)
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
