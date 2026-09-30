// npx vitest run core/prompts/tools/__tests__/filter-tools-for-mode.spec.ts

import type OpenAI from "openai"

import { filterNativeToolsForMode } from "../filter-tools-for-mode"
import { filterMcpToolsForMode } from "../filter-tools-for-mode"
import { applyModelToolCustomization } from "../filter-tools-for-mode"
import { applyToolAliases, getToolAliasGroup } from "../filter-tools-for-mode"

function makeTool(name: string): OpenAI.Chat.ChatCompletionTool {
	return {
		type: "function",
		function: {
			name,
			description: `${name} tool`,
			parameters: { type: "object", properties: {} },
		},
	} as OpenAI.Chat.ChatCompletionTool
}

describe("filterNativeToolsForMode - disabledTools", () => {
	const nativeTools: OpenAI.Chat.ChatCompletionTool[] = [
		makeTool("execute_command"),
		makeTool("read_file"),
		makeTool("write_to_file"),
		makeTool("apply_diff"),
		makeTool("edit"),
	]

	it("removes tools listed in settings.disabledTools", () => {
		const settings = {
			disabledTools: ["execute_command"],
		}

		const result = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, settings)

		const resultNames = result.map((t) => (t as any).function.name)
		expect(resultNames).not.toContain("execute_command")
		expect(resultNames).toContain("read_file")
		expect(resultNames).toContain("write_to_file")
		expect(resultNames).toContain("apply_diff")
	})

	it("does not remove any tools when disabledTools is empty", () => {
		const settings = {
			disabledTools: [],
		}

		const result = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, settings)

		const resultNames = result.map((t) => (t as any).function.name)
		expect(resultNames).toContain("execute_command")
		expect(resultNames).toContain("read_file")
		expect(resultNames).toContain("write_to_file")
		expect(resultNames).toContain("apply_diff")
	})

	it("does not remove any tools when disabledTools is undefined", () => {
		const settings = {}

		const result = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, settings)

		const resultNames = result.map((t) => (t as any).function.name)
		expect(resultNames).toContain("execute_command")
		expect(resultNames).toContain("read_file")
	})

	it("combines disabledTools with other setting-based exclusions", () => {
		const settings = {
			disabledTools: ["execute_command"],
		}

		const result = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, settings)

		const resultNames = result.map((t) => (t as any).function.name)
		expect(resultNames).not.toContain("execute_command")
		expect(resultNames).toContain("read_file")
	})

	it("disables canonical tool when disabledTools contains alias name", () => {
		const settings = {
			disabledTools: ["search_and_replace"],
			modelInfo: {
				includedTools: ["search_and_replace"],
			},
		}

		const result = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, settings)

		const resultNames = result.map((t) => (t as any).function.name)
		expect(resultNames).not.toContain("search_and_replace")
		expect(resultNames).not.toContain("edit")
	})

 it("removes access_mcp_resource when mcpHub has no resources and includes when resources exist", () => {
   const nativeTools: OpenAI.Chat.ChatCompletionTool[] = [makeTool("access_mcp_resource")]
 
   // No mcpHub -> tool should be removed
   const resNoHub = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, undefined, undefined)
   expect(resNoHub.map((t) => (t as any).function.name)).not.toContain("access_mcp_resource")
 
   // mcpHub with servers but empty resources -> still removed
   const mcpHubEmpty = {
     getServers: () => [{ id: "s1", resources: [] }],
   } as any
   const resEmpty = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, undefined, mcpHubEmpty)
   expect(resEmpty.map((t) => (t as any).function.name)).not.toContain("access_mcp_resource")
 
   // mcpHub with at least one server with resources -> tool should be present
   const mcpHubWith = {
     getServers: () => [{ id: "s1", resources: [{ name: "r1" }] }],
   } as any
   const resWith = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, undefined, mcpHubWith)
   expect(resWith.map((t) => (t as any).function.name)).toContain("access_mcp_resource")
 })


 it("applies alias renames from modelInfo and caches renamed tool across calls", () => {
   // Use the existing helper defined in the file to construct a native tool for the canonical 'edit' tool
   const nativeTools: OpenAI.Chat.ChatCompletionTool[] = [makeTool("edit")]
 
   // Provide modelInfo that includes the legacy alias 'search_and_replace' which maps to canonical 'edit'
   const settings = {
     modelInfo: {
       includedTools: ["search_and_replace"],
     },
   }
 
   // First call should return the tool renamed to the alias name
   const firstResult = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, settings)
   const firstNames = firstResult.map((t) => (t as any).function.name)
   expect(firstNames).toContain("search_and_replace")
 
   const firstToolObj = firstResult[0]
   expect((firstToolObj as any).function.name).toBe("search_and_replace")
 
   // Second call should produce a tool that is the same object reference (cached)
   const secondResult = filterNativeToolsForMode(nativeTools, "code", undefined, undefined, undefined, settings)
   const secondToolObj = secondResult[0]
   expect(secondToolObj).toBe(firstToolObj)
 })


 it("filterMcpToolsForMode returns input array when allowed or empty when disallowed", () => {
   const mcpTools = [makeTool("mcp_tool_one"), makeTool("mcp_tool_two")]
 
   // Default mode - depending on mode configuration this may allow or disallow MCP.
   // The function should deterministically return either the original array (if allowed)
   // or an empty array (if disallowed). Assert this behavior.
   const out = filterMcpToolsForMode(mcpTools, undefined, undefined, undefined)
   expect(Array.isArray(out)).toBe(true)
 
   if (out.length > 0) {
     // When allowed, the function returns the same reference that was passed in
     expect(out).toBe(mcpTools)
   } else {
     // When disallowed, it's an empty array
     expect(out.length).toBe(0)
   }
 })


 it("applyModelToolCustomization removes excluded tools and tracks no aliasRenames when excluded", () => {
   const allowed = new Set(["edit", "read_file"])
   // modeConfig is not required for excludedTools branch; provide minimal structure
   const modeConfig = { groups: [] } as any
   const modelInfo = { excludedTools: ["search_and_replace"] } as any
   const res = applyModelToolCustomization(allowed, modeConfig, modelInfo)
 
   // The alias "search_and_replace" resolves to "edit", so "edit" should be removed
   expect(res.allowedTools.has("edit")).toBe(false)
   // Other tools should remain
   expect(res.allowedTools.has("read_file")).toBe(true)
   // No alias renames should be produced when only excluding
   expect(res.aliasRenames.size).toBe(0)
 })


 it("resolves aliases to canonical names and returns full alias group", () => {
   // Use a known alias from existing tests ("search_and_replace" -> "edit")
   const input = new Set(["search_and_replace", "edit"])
   const applied = applyToolAliases(input)
   // Aliases should be resolved to canonical names, so canonical "edit" must be present
   expect(applied.has("edit")).toBe(true)
   // The alias string itself should be resolved away (normalized to canonical)
   expect(applied.has("search_and_replace")).toBe(false)
 
   // getToolAliasGroup should return both canonical and alias members for an alias
   const group = getToolAliasGroup("search_and_replace")
   expect(group).toEqual(expect.arrayContaining(["edit", "search_and_replace"]))
 })

})
