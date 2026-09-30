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


  __testAugmentVitest_6c1b0419321a.it("deduplicate_non_name_captures_round_026_pass_03", async () => {
  	// Arrange: file exists
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({ fileExistsAtPath: () => Promise.resolve(true) }))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({ readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("dup\nline2\n") }))

  	// Two non-name captures resolving to the same start/end -> second should be skipped by processedLines.has
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			js: {
  				parser: { parse: (c: string) => ({ rootNode: {} }) },
  				query: { captures: (rootNode: any) => {
  					const nodeA = { startPosition: { row: 0 }, endPosition: { row: 0 }, parent: null, text: "dup" }
  					const nodeB = { startPosition: { row: 0 }, endPosition: { row: 0 }, parent: null, text: "dup" }
  					return [ { node: nodeA, name: "other.definition" }, { node: nodeB, name: "other.definition" } ]
  				} }
  			}
  		})
  	}))

  	// Act
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()
  	setMinComponentLines(1)
  	const result = await parseSourceCodeDefinitionsForFile("dupNonName.js")

  	// Assert: only one occurrence should be present
  	__testAugmentVitest_6c1b0419321a.expect(result).toBeDefined()
  	const occurrences = (result as string).split("1--1 | dup").length - 1
  	__testAugmentVitest_6c1b0419321a.expect(occurrences).toBe(1)
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
