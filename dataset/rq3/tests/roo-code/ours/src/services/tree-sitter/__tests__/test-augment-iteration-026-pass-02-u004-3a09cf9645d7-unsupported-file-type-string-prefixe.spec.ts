// Mocks must come first, before imports

vi.mock("fs/promises", () => ({
	readFile: vi.fn().mockImplementation(() => Promise.resolve("")),
	stat: vi.fn().mockImplementation(() => Promise.resolve({ isDirectory: () => false })),
}))

vi.mock("../../../utils/fs", () => ({
	fileExistsAtPath: vi.fn().mockImplementation(() => Promise.resolve(true)),
}))

// Then imports
import * as fs from "fs/promises"
import type { Mock } from "vitest"

import { parseSourceCodeDefinitionsForFile } from "../index"

describe("Markdown Integration Tests", () => {
	beforeEach(() => {
		vi.clearAllMocks()
	})


  __testAugmentVitest_6c1b0419321a.it("returns Unsupported file type string prefixed by filename_round_026_pass_02", async () => {
  	// Arrange: file exists and readFile (content not important)
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({
  		fileExistsAtPath: () => Promise.resolve(true),
  	}))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({
  		readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("ignored content\n")
  	}))

  	// Provide languageParsers entry for 'js' but without parser/query to trigger Unsupported file type branch
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			js: {},
  		}),
  	}))

  	// Act
  	const { parseSourceCodeDefinitionsForFile } = await __testAugmentLoadTarget_7ece0c5ff963()
  	const result = await parseSourceCodeDefinitionsForFile("file.js")

  	// Assert: the returned string should include the header and the Unsupported message
  	__testAugmentVitest_6c1b0419321a.expect(result).toBe(`# file.js\nUnsupported file type: file.js`)
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
