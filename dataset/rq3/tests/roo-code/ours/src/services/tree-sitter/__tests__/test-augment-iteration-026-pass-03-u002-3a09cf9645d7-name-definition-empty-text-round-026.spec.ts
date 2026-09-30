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


  __testAugmentVitest_6c1b0419321a.it("name_definition_empty_text_round_026_pass_03", async () => {
  	// Arrange
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({ fileExistsAtPath: () => Promise.resolve(true) }))
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({ readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue("Comp\nbody\nend\n") }))

  	// Provide a name.definition capture whose node.text is empty -> componentName falsy
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			js: {
  				parser: { parse: (c: string) => ({ rootNode: {} }) },
  				query: { captures: (rootNode: any) => [
  					{ node: { text: "", startPosition: { row: 0 }, endPosition: { row: 0 }, parent: { startPosition: { row: 0 }, endPosition: { row: 1 } } }, name: "name.definition" }
  				] }
  			}
  		})
  	}))

  	// Act
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()
  	setMinComponentLines(1)
  	const result = await parseSourceCodeDefinitionsForFile("emptyname.js")

  	// Assert: empty component name should be ignored -> overall undefined
  	__testAugmentVitest_6c1b0419321a.expect(result).toBeUndefined()
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
