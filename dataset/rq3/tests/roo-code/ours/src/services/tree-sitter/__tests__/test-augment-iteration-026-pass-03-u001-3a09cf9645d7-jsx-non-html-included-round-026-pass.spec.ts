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


  __testAugmentVitest_6c1b0419321a.it("jsx_non_html_included_round_026_pass_03", async () => {
  	// Arrange: ensure file exists and content has a non-HTML first line
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({ fileExistsAtPath: () => Promise.resolve(true) }))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({ readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("const x = 1\nconsole.log(x)\n") }))

  	// Mock language parser for jsx with a capture whose start line is NOT an HTML element
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			jsx: {
  				parser: { parse: (c: string) => ({ rootNode: {} }) },
  				query: { captures: (rootNode: any) => [
  					{
  						node: {
  							startPosition: { row: 0 },
  							endPosition: { row: 1 },
  							parent: { startPosition: { row: 0 }, endPosition: { row: 1 }, lastChild: { endPosition: { row: 1 } }, text: "parent" },
  							text: "unused"
  						},
  						name: "function.definition"
  					}
  				] }
  			}
  		})
  	}))

  	// Act
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()
  	setMinComponentLines(1)
  	const result = await parseSourceCodeDefinitionsForFile("component.jsx")

  	// Assert: the non-HTML line is included (isNotHtmlElement should return true)
  	__testAugmentVitest_6c1b0419321a.expect(result).toBeDefined()
  	__testAugmentVitest_6c1b0419321a.expect((result as string)).toContain("# component.jsx")
  	__testAugmentVitest_6c1b0419321a.expect((result as string)).toContain("1--2 | const x = 1")
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
