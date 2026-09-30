// npx vitest services/tree-sitter/__tests__/languageParser.spec.ts

import * as path from "path"
import { loadRequiredLanguageParsers } from "../languageParser"

// Path to the directory containing the WASM files.
const WASM_DIR = path.join(__dirname, "../../../node_modules/tree-sitter-wasms/out")

describe("loadRequiredLanguageParsers", () => {





  __testAugmentVitest_8ffdcda413b1.it("unsupported_extension_throws_round_019", async () => {
  	// Benign mock so the module loads deterministically, but the switch default should still throw
  	__testAugmentVitest_8ffdcda413b1.vi.doMock("web-tree-sitter", () => {
  		return {
  			Parser: class { static async init() {} constructor() {} setLanguage() {} },
  			Query: function() { return {} },
  			Language: { load: async (p) => ({ wasm: p }) }
  		}
  	})

  	const mod = await __testAugmentLoadTarget_7946ce1a0977()
  	const { loadRequiredLanguageParsers } = mod

  	await __testAugmentVitest_8ffdcda413b1.expect(loadRequiredLanguageParsers(["some.unsupported"], WASM_DIR)).rejects.toThrow("Unsupported language: unsupported")
  })
})

import * as __testAugmentVitest_8ffdcda413b1 from "vitest";

const __testAugmentLoadTarget_7946ce1a0977 = async () => {
  __testAugmentVitest_8ffdcda413b1.vi.doUnmock("../languageParser.js");
  __testAugmentVitest_8ffdcda413b1.vi.resetModules();
  return import("../languageParser.js");
};
