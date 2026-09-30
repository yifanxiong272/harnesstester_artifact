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


  __testAugmentVitest_6c1b0419321a.it("skips_short_components_below_min_lines_round_026_pass_02", async () => {
  	// Arrange: file exists and simple one-line content
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({ fileExistsAtPath: () => Promise.resolve(true) }))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({ readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("only one line\n") }))

  	// Mock parser that yields a definition whose span is 1 line
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			js: {
  				parser: { parse: (c: string) => ({ rootNode: {} }) },
  				query: { captures: (rootNode: any) => [
  					{ node: { startPosition: { row: 0 }, endPosition: { row: 0 }, parent: null, text: "f" }, name: "function.definition" }
  				] },
  			},
  		}),
  	}))

  	// Act
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()
  	// raise minimum so the 1-line component is filtered out
  	setMinComponentLines(3)
  	const result = await parseSourceCodeDefinitionsForFile("short.js")

  	// Assert: component shorter than min lines is skipped
  	__testAugmentVitest_6c1b0419321a.expect(result).toBeUndefined()
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
