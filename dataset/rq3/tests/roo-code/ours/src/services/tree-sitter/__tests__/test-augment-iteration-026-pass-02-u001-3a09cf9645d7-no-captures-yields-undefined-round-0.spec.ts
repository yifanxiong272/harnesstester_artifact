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


  __testAugmentVitest_6c1b0419321a.it("returns undefined when parser yields no captures_round_026_pass_02", async () => {
  	// Arrange: ensure file existence and provide file content
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({
  		fileExistsAtPath: () => Promise.resolve(true),
  	}))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({
  		readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("const a = 1\nconst b = 2\n")
  	}))

  	// Mock language parser to produce an AST but zero captures
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			js: {
  				parser: { parse: (c: string) => ({ rootNode: {} }) },
  				query: { captures: (rootNode: any) => [] },
  			},
  		}),
  	}))

  	// Act: load the module AFTER mocks and invoke the function
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()
  	// lower threshold to avoid accidental filtering
  	setMinComponentLines(1)
  	const result = await parseSourceCodeDefinitionsForFile("silent.js")

  	// Assert: no definitions returned when captures are empty
  	__testAugmentVitest_6c1b0419321a.expect(result).toBeUndefined()
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
