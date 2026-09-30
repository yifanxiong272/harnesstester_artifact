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


  __testAugmentVitest_6c1b0419321a.it("filters out HTML-like lines in JSX and returns undefined_round_026_pass_02", async () => {
  	// Arrange: file exists and contains an HTML-like line
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({
  		fileExistsAtPath: () => Promise.resolve(true),
  	}))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({
  		readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("<div>hello</div>\n")
  	}))

  	// Mock language parser for jsx; provide a capture whose start line contains an HTML element
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			jsx: {
  				parser: { parse: (c: string) => ({ rootNode: {} }) },
  				query: { captures: (rootNode: any) => [
  					{
  						node: { startPosition: { row: 0 }, parent: null, text: "<div>hello</div>" },
  						name: "some.definition"
  					}
  				] },
  			},
  		}),
  	}))

  	// Act
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()
  	setMinComponentLines(1)
  	const result = await parseSourceCodeDefinitionsForFile("component.jsx")

  	// Assert: HTML-like line should be filtered out and no definitions returned
  	__testAugmentVitest_6c1b0419321a.expect(result).toBeUndefined()
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
