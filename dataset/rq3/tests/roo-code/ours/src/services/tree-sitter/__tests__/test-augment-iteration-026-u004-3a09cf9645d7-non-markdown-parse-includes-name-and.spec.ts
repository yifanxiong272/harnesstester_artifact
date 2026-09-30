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


  __testAugmentVitest_6c1b0419321a.it("parses non-markdown file using mocked language parsers and includes name.definition and context ranges_round_026", async () => {
  	// Prepare file content with multiple lines; indices used in captures must match
  	const fileContent = [
  		"function Comp() {", // line 0
  		"  // body",          // line 1
  		"}",                 // line 2
  		"// trailing line"    // line 3 (used as context end)
  	].join("\n")

  	// Mock fs.readFile to return the prepared content
  	__testAugmentVitest_6c1b0419321a.vi.doMock("fs/promises", () => ({
  		readFile: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue(fileContent)
  	}))

  	// Ensure the file-exists helper returns true
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../../../utils/fs", () => ({
  		fileExistsAtPath: () => Promise.resolve(true),
  	}))

  	// Mock the language parser module so parseSourceCodeDefinitionsForFile uses our fake parser and query
  	__testAugmentVitest_6c1b0419321a.vi.doMock("../languageParser", () => ({
  		loadRequiredLanguageParsers: __testAugmentVitest_6c1b0419321a.vi.fn().mockResolvedValue({
  			js: {
  				parser: {
  					parse: (content: string) => ({ rootNode: {} }),
  				},
  				query: {
  					captures: (rootNode: any) => {
  						// Build two captures: one with a name.definition (uses node.parent as definitionNode)
  						// and another non-name capture (e.g., function.definition) to exercise the context inclusion branch
  						const parentNode = {
  							startPosition: { row: 0 },
  							endPosition: { row: 2 },
  							lastChild: { endPosition: { row: 3 } },
  							text: "function Comp() {",
  						}

  						const nameNode = {
  							text: "Comp",
  							parent: parentNode,
  							startPosition: { row: 0 },
  							endPosition: { row: 0 },
  						}

  						const otherNode = {
  							text: "function",
  							parent: parentNode,
  							startPosition: { row: 0 },
  							endPosition: { row: 0 }
  						}

  						return [
  							{ node: nameNode, name: "name.definition" },
  							{ node: otherNode, name: "function.definition" },
  						]
  					}
  				}
  			}
  		})
  	}))

  	// Load the target module so it uses the above mocks
  	const { parseSourceCodeDefinitionsForFile, setMinComponentLines } = await __testAugmentLoadTarget_7ece0c5ff963()

  	// Lower the minimum lines to include our small example (avoid depending on the default)
  	setMinComponentLines(1)

  	const result = await parseSourceCodeDefinitionsForFile("example.js")

  	__testAugmentVitest_6c1b0419321a.expect(result).toBeDefined()
  	__testAugmentVitest_6c1b0419321a.expect(result).toContain("# example.js")
  	// Expect the name.definition capture to produce the short range (1-based line numbers)
  	__testAugmentVitest_6c1b0419321a.expect(result).toContain("1--3 | function Comp() {")
  	// Expect the context inclusion to add the broader context range (parent.start to lastChild.end)
  	__testAugmentVitest_6c1b0419321a.expect(result).toContain("1--4 | function Comp() {")
  })
})

import * as __testAugmentVitest_6c1b0419321a from "vitest";

const __testAugmentLoadTarget_7ece0c5ff963 = async () => {
  __testAugmentVitest_6c1b0419321a.vi.doUnmock("../index.js");
  __testAugmentVitest_6c1b0419321a.vi.resetModules();
  return import("../index.js");
};
