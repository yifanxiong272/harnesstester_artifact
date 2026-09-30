// npx vitest services/tree-sitter/__tests__/languageParser.spec.ts

import * as path from "path"
import { loadRequiredLanguageParsers } from "../languageParser"

// Path to the directory containing the WASM files.
const WASM_DIR = path.join(__dirname, "../../../node_modules/tree-sitter-wasms/out")

describe("loadRequiredLanguageParsers", () => {
	it("should load Python parser for .py files", async () => {
		const files = ["test.py"]
		const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
		expect(parsers.py).toBeDefined()
	})

	it("should load JavaScript parser for .js and .jsx files", async () => {
		const files = ["test.js", "test.jsx"]
		const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
		expect(parsers.js).toBeDefined()
		expect(parsers.jsx).toBeDefined()
		expect(parsers.js.query).toBeDefined()
		expect(parsers.jsx.query).toBeDefined()
	})

	it("should load multiple language parsers as needed", async () => {
		const files = ["test.js", "test.py", "test.rs", "test.go"]
		const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
		expect(parsers.js).toBeDefined()
		expect(parsers.py).toBeDefined()
		expect(parsers.rs).toBeDefined()
		expect(parsers.go).toBeDefined()
	})

	it("should handle C/C++ files correctly", async () => {
		const files = ["test.c", "test.h", "test.cpp", "test.hpp"]
		const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
		expect(parsers.c).toBeDefined()
		expect(parsers.h).toBeDefined()
		expect(parsers.cpp).toBeDefined()
		expect(parsers.hpp).toBeDefined()
	})

	it("should handle Kotlin files correctly", async () => {
		const files = ["test.kt", "test.kts"]
		const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
		expect(parsers.kt).toBeDefined()
		expect(parsers.kts).toBeDefined()
		expect(parsers.kt.query).toBeDefined()
		expect(parsers.kts.query).toBeDefined()
	})

	it("should throw error for unsupported file extensions", async () => {
		const files = ["test.unsupported"]
		await expect(loadRequiredLanguageParsers(files, WASM_DIR)).rejects.toThrow("Unsupported language: unsupported")
	})

 it("should load C# Ruby and Elixir parsers", async () => {
   const files = ["one.cs", "two.rb", "three.ex", "four.exs"]
   const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
   expect(parsers.cs).toBeDefined()
   expect(parsers.cs.query).toBeDefined()
   expect(parsers.rb).toBeDefined()
   expect(parsers.rb.query).toBeDefined()
   expect(parsers.ex).toBeDefined()
   expect(parsers.exs).toBeDefined()
   // Queries for Elixir should also be present
   expect(parsers.ex.query).toBeDefined()
   expect(parsers.exs.query).toBeDefined()
 })


 it("should map .ejs and .erb to embedded_template parser key", async () => {
   const files = ["template.ejs", "template.erb"]
   const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
   // Both .ejs and .erb map to a single parserKey "embedded_template"
   expect(parsers.embedded_template).toBeDefined()
   // there should not be separate keys for ejs or erb
   expect(parsers.ejs).toBeUndefined()
   expect(parsers.erb).toBeUndefined()
   // the shared parser should include a query
   expect(parsers.embedded_template.query).toBeDefined()
 })


 it("should load TypeScript and TSX parsers", async () => {
   const files = ["file.ts", "file.tsx"]
   const parsers = await loadRequiredLanguageParsers(files, WASM_DIR)
   expect(parsers.ts).toBeDefined()
   expect(parsers.ts.query).toBeDefined()
   expect(parsers.tsx).toBeDefined()
   expect(parsers.tsx.query).toBeDefined()
 })

})
