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


  __testAugmentVitest_6c1b0419321a.it("parent_no_lastChild_skips_context_round_026_pass_03", async () => {
  	// Arrange: file with two lines; start line content is not HTML-like
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({ fileExistsAtPath: () => Promise.resolve(true) }))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({ readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("const val = 42\n// comment\n") }))

  	// Mock parser: single non-name capture with parent that has NO lastChild -> context-block skipped
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			js: {
  				parser: { parse: (c: string) => ({ rootNode: {} }) },
  				query: { captures: (rootNode: any) => [
  					{ node: { startPosition: { row: 0 }, endPosition: { row: 0 }, parent: { startPosition: { row: 0 }, endPosition: { row: 0 }, lastChild: null }, text: "const val = 42" }, name: "variable.definition" }
  				] }
  			}
  		})
  	}))

  	// Act
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()
  	setMinComponentLines(1)
  	const result = await parseSourceCodeDefinitionsForFile("noctx.js")

  	// Assert: the short range should be present but no larger parent context range should be added
  	__testAugmentVitest_6c1b0419321a.expect(result).toBeDefined()
  	__testAugmentVitest_6c1b0419321a.expect((result as string)).toContain("1--1 | const val = 42")
  	// There should be no extended multi-line parent range (which would be '1--<n> |')
  	__testAugmentVitest_6c1b0419321a.expect((result as string)).not.toContain("1--2 | const val = 42")
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
