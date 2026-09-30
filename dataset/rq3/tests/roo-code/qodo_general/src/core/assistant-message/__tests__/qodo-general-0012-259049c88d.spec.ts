import { NativeToolCallParser } from "../NativeToolCallParser"
import { customToolRegistry } from "@roo-code/core"

describe("NativeToolCallParser", () => {
	beforeEach(() => {
		NativeToolCallParser.clearAllStreamingToolCalls()
		NativeToolCallParser.clearRawChunkState()
	})

	describe("parseToolCall", () => {
		describe("read_file tool", () => {
			it("should parse minimal single-file read_file args", () => {
				const toolCall = {
					id: "toolu_123",
					name: "read_file" as const,
					arguments: JSON.stringify({
						path: "src/core/task/Task.ts",
					}),
				}

				const result = NativeToolCallParser.parseToolCall(toolCall)

				expect(result).not.toBeNull()
				expect(result?.type).toBe("tool_use")
				if (result?.type === "tool_use") {
					expect(result.nativeArgs).toBeDefined()
					const nativeArgs = result.nativeArgs as { path: string }
					expect(nativeArgs.path).toBe("src/core/task/Task.ts")
				}
			})

			it("should parse slice-mode params", () => {
				const toolCall = {
					id: "toolu_123",
					name: "read_file" as const,
					arguments: JSON.stringify({
						path: "src/core/task/Task.ts",
						mode: "slice",
						offset: 10,
						limit: 20,
					}),
				}

				const result = NativeToolCallParser.parseToolCall(toolCall)

				expect(result).not.toBeNull()
				expect(result?.type).toBe("tool_use")
				if (result?.type === "tool_use") {
					const nativeArgs = result.nativeArgs as {
						path: string
						mode?: string
						offset?: number
						limit?: number
					}
					expect(nativeArgs.path).toBe("src/core/task/Task.ts")
					expect(nativeArgs.mode).toBe("slice")
					expect(nativeArgs.offset).toBe(10)
					expect(nativeArgs.limit).toBe(20)
				}
			})

			it("should parse indentation-mode params", () => {
				const toolCall = {
					id: "toolu_123",
					name: "read_file" as const,
					arguments: JSON.stringify({
						path: "src/utils.ts",
						mode: "indentation",
						indentation: {
							anchor_line: 123,
							max_levels: 2,
							include_siblings: true,
							include_header: false,
						},
					}),
				}

				const result = NativeToolCallParser.parseToolCall(toolCall)

				expect(result).not.toBeNull()
				expect(result?.type).toBe("tool_use")
				if (result?.type === "tool_use") {
					const nativeArgs = result.nativeArgs as {
						path: string
						mode?: string
						indentation?: {
							anchor_line?: number
							max_levels?: number
							include_siblings?: boolean
							include_header?: boolean
						}
					}
					expect(nativeArgs.path).toBe("src/utils.ts")
					expect(nativeArgs.mode).toBe("indentation")
					expect(nativeArgs.indentation?.anchor_line).toBe(123)
					expect(nativeArgs.indentation?.include_siblings).toBe(true)
					expect(nativeArgs.indentation?.include_header).toBe(false)
				}
			})

			// Legacy format backward compatibility tests
			describe("legacy format backward compatibility", () => {
				it("should parse legacy files array format with single file", () => {
					const toolCall = {
						id: "toolu_legacy_1",
						name: "read_file" as const,
						arguments: JSON.stringify({
							files: [{ path: "src/legacy/file.ts" }],
						}),
					}

					const result = NativeToolCallParser.parseToolCall(toolCall)

					expect(result).not.toBeNull()
					expect(result?.type).toBe("tool_use")
					if (result?.type === "tool_use") {
						expect(result.usedLegacyFormat).toBe(true)
						const nativeArgs = result.nativeArgs as { files: Array<{ path: string }>; _legacyFormat: true }
						expect(nativeArgs._legacyFormat).toBe(true)
						expect(nativeArgs.files).toHaveLength(1)
						expect(nativeArgs.files[0].path).toBe("src/legacy/file.ts")
					}
				})

				it("should parse legacy files array format with multiple files", () => {
					const toolCall = {
						id: "toolu_legacy_2",
						name: "read_file" as const,
						arguments: JSON.stringify({
							files: [{ path: "src/file1.ts" }, { path: "src/file2.ts" }, { path: "src/file3.ts" }],
						}),
					}

					const result = NativeToolCallParser.parseToolCall(toolCall)

					expect(result).not.toBeNull()
					expect(result?.type).toBe("tool_use")
					if (result?.type === "tool_use") {
						expect(result.usedLegacyFormat).toBe(true)
						const nativeArgs = result.nativeArgs as { files: Array<{ path: string }>; _legacyFormat: true }
						expect(nativeArgs.files).toHaveLength(3)
						expect(nativeArgs.files[0].path).toBe("src/file1.ts")
						expect(nativeArgs.files[1].path).toBe("src/file2.ts")
						expect(nativeArgs.files[2].path).toBe("src/file3.ts")
					}
				})

				it("should parse legacy line_ranges as tuples", () => {
					const toolCall = {
						id: "toolu_legacy_3",
						name: "read_file" as const,
						arguments: JSON.stringify({
							files: [
								{
									path: "src/task.ts",
									line_ranges: [
										[1, 50],
										[100, 150],
									],
								},
							],
						}),
					}

					const result = NativeToolCallParser.parseToolCall(toolCall)

					expect(result).not.toBeNull()
					expect(result?.type).toBe("tool_use")
					if (result?.type === "tool_use") {
						expect(result.usedLegacyFormat).toBe(true)
						const nativeArgs = result.nativeArgs as {
							files: Array<{ path: string; lineRanges?: Array<{ start: number; end: number }> }>
							_legacyFormat: true
						}
						expect(nativeArgs.files[0].lineRanges).toHaveLength(2)
						expect(nativeArgs.files[0].lineRanges?.[0]).toEqual({ start: 1, end: 50 })
						expect(nativeArgs.files[0].lineRanges?.[1]).toEqual({ start: 100, end: 150 })
					}
				})

				it("should parse legacy line_ranges as objects", () => {
					const toolCall = {
						id: "toolu_legacy_4",
						name: "read_file" as const,
						arguments: JSON.stringify({
							files: [
								{
									path: "src/task.ts",
									line_ranges: [
										{ start: 10, end: 20 },
										{ start: 30, end: 40 },
									],
								},
							],
						}),
					}

					const result = NativeToolCallParser.parseToolCall(toolCall)

					expect(result).not.toBeNull()
					expect(result?.type).toBe("tool_use")
					if (result?.type === "tool_use") {
						expect(result.usedLegacyFormat).toBe(true)
						const nativeArgs = result.nativeArgs as {
							files: Array<{ path: string; lineRanges?: Array<{ start: number; end: number }> }>
						}
						expect(nativeArgs.files[0].lineRanges).toHaveLength(2)
						expect(nativeArgs.files[0].lineRanges?.[0]).toEqual({ start: 10, end: 20 })
						expect(nativeArgs.files[0].lineRanges?.[1]).toEqual({ start: 30, end: 40 })
					}
				})

				it("should parse legacy line_ranges as strings", () => {
					const toolCall = {
						id: "toolu_legacy_5",
						name: "read_file" as const,
						arguments: JSON.stringify({
							files: [
								{
									path: "src/task.ts",
									line_ranges: ["1-50", "100-150"],
								},
							],
						}),
					}

					const result = NativeToolCallParser.parseToolCall(toolCall)

					expect(result).not.toBeNull()
					expect(result?.type).toBe("tool_use")
					if (result?.type === "tool_use") {
						expect(result.usedLegacyFormat).toBe(true)
						const nativeArgs = result.nativeArgs as {
							files: Array<{ path: string; lineRanges?: Array<{ start: number; end: number }> }>
						}
						expect(nativeArgs.files[0].lineRanges).toHaveLength(2)
						expect(nativeArgs.files[0].lineRanges?.[0]).toEqual({ start: 1, end: 50 })
						expect(nativeArgs.files[0].lineRanges?.[1]).toEqual({ start: 100, end: 150 })
					}
				})

				it("should parse double-stringified files array (model quirk)", () => {
					// This tests the real-world case where some models double-stringify the files array
					// e.g., { files: "[{\"path\": \"...\"}]" } instead of { files: [{path: "..."}] }
					const toolCall = {
						id: "toolu_double_stringify",
						name: "read_file" as const,
						arguments: JSON.stringify({
							files: JSON.stringify([
								{ path: "src/services/example/service.ts" },
								{ path: "src/services/mcp/McpServerManager.ts" },
							]),
						}),
					}

					const result = NativeToolCallParser.parseToolCall(toolCall)

					expect(result).not.toBeNull()
					expect(result?.type).toBe("tool_use")
					if (result?.type === "tool_use") {
						expect(result.usedLegacyFormat).toBe(true)
						const nativeArgs = result.nativeArgs as {
							files: Array<{ path: string }>
							_legacyFormat: true
						}
						expect(nativeArgs._legacyFormat).toBe(true)
						expect(nativeArgs.files).toHaveLength(2)
						expect(nativeArgs.files[0].path).toBe("src/services/example/service.ts")
						expect(nativeArgs.files[1].path).toBe("src/services/mcp/McpServerManager.ts")
					}
				})

				it("should NOT set usedLegacyFormat for new format", () => {
					const toolCall = {
						id: "toolu_new",
						name: "read_file" as const,
						arguments: JSON.stringify({
							path: "src/new/format.ts",
							mode: "slice",
							offset: 1,
							limit: 100,
						}),
					}

					const result = NativeToolCallParser.parseToolCall(toolCall)

					expect(result).not.toBeNull()
					expect(result?.type).toBe("tool_use")
					if (result?.type === "tool_use") {
						expect(result.usedLegacyFormat).toBeUndefined()
					}
				})
			})
		})
	})

	describe("processStreamingChunk", () => {
		describe("read_file tool", () => {
			it("should emit a partial ToolUse with nativeArgs.path during streaming", () => {
				const id = "toolu_streaming_123"
				NativeToolCallParser.startStreamingToolCall(id, "read_file")

				// Simulate streaming chunks
				const fullArgs = JSON.stringify({ path: "src/test.ts" })

				// Process the complete args as a single chunk for simplicity
				const result = NativeToolCallParser.processStreamingChunk(id, fullArgs)

				expect(result).not.toBeNull()
				expect(result?.nativeArgs).toBeDefined()
				const nativeArgs = result?.nativeArgs as { path: string }
				expect(nativeArgs.path).toBe("src/test.ts")
			})
		})
	})

	describe("finalizeStreamingToolCall", () => {
		describe("read_file tool", () => {
			it("should parse read_file args on finalize", () => {
				const id = "toolu_finalize_123"
				NativeToolCallParser.startStreamingToolCall(id, "read_file")

				// Add the complete arguments
				NativeToolCallParser.processStreamingChunk(
					id,
					JSON.stringify({
						path: "finalized.ts",
						mode: "slice",
						offset: 1,
						limit: 10,
					}),
				)

				const result = NativeToolCallParser.finalizeStreamingToolCall(id)

				expect(result).not.toBeNull()
				expect(result?.type).toBe("tool_use")
				if (result?.type === "tool_use") {
					const nativeArgs = result.nativeArgs as { path: string; offset?: number; limit?: number }
					expect(nativeArgs.path).toBe("finalized.ts")
					expect(nativeArgs.offset).toBe(1)
					expect(nativeArgs.limit).toBe(10)
				}
			})

   it("should coerce string 'true' for replace_all into boolean true for edit tool", () => {
     const toolCall = {
       id: "edit_1",
       name: "edit" as const,
       arguments: JSON.stringify({
         file_path: "a.ts",
         old_string: "x",
         new_string: "y",
         replace_all: "true",
       }),
     }
   
     const result = NativeToolCallParser.parseToolCall(toolCall)
     expect(result).not.toBeNull()
     if (result?.type === "tool_use") {
       const nativeArgs = result.nativeArgs as any
       expect(nativeArgs.file_path).toBe("a.ts")
       // coerceOptionalBoolean should convert the string "true" into boolean true
       expect(nativeArgs.replace_all).toBe(true)
     }
   })


   it("should accept any args for a custom tool when customToolRegistry.has returns true", () => {
     // Import is provided via new_imports_code; mutate the registry directly to avoid spy helpers
     const originalHas = customToolRegistry.has
     ;(customToolRegistry as any).has = () => true
   
     try {
       const toolCall = {
         id: "custom_1",
         name: "my_custom_tool" as unknown as any,
         arguments: JSON.stringify({ anything: 123, nested: { a: "b" } }),
       }
   
       const result = NativeToolCallParser.parseToolCall(toolCall as any)
       expect(result).not.toBeNull()
       if (result?.type === "tool_use") {
         // For custom tools the parser should place the raw parsed args into nativeArgs
         expect(result.nativeArgs).toEqual({ anything: 123, nested: { a: "b" } })
       } else {
         throw new Error("Expected tool_use result for custom tool")
       }
     } finally {
       // restore original method
       ;(customToolRegistry as any).has = originalHas
     }
   })


   it("should return null for core tool when required args are missing (apply_diff missing diff)", () => {
     const toolCall = {
       id: "bad_apply",
       name: "apply_diff" as const,
       // missing 'diff' field - only path provided
       arguments: JSON.stringify({ path: "src/some/file.ts" }),
     }
     const result = NativeToolCallParser.parseToolCall(toolCall)
     expect(result).toBeNull()
   })


   it("should coerce string booleans in indentation object", () => {
     const toolCall = {
       id: "read_file_bool",
       name: "read_file" as const,
       arguments: JSON.stringify({
         path: "file.ts",
         mode: "indentation",
         indentation: {
           anchor_line: "5",
           max_levels: "3",
           include_siblings: "true",
           include_header: "false",
         },
       }),
     }
   
     const result = NativeToolCallParser.parseToolCall(toolCall)
     expect(result).not.toBeNull()
     if (result?.type === "tool_use") {
       const nativeArgs = result.nativeArgs as any
       expect(nativeArgs.path).toBe("file.ts")
       // Numeric strings should be coerced to numbers
       expect(nativeArgs.indentation.anchor_line).toBe(5)
       expect(nativeArgs.indentation.max_levels).toBe(3)
       // Boolean strings should be coerced to booleans
       expect(nativeArgs.indentation.include_siblings).toBe(true)
       expect(nativeArgs.indentation.include_header).toBe(false)
     } else {
       fail("Expected a ToolUse result for read_file")
     }
   })


   it("should return null for unknown tool names", () => {
     const toolCall = {
       id: "bad1",
       name: "nonexistent_tool_xyz" as any,
       arguments: "{}",
     }
     const result = NativeToolCallParser.parseToolCall(toolCall)
     expect(result).toBeNull()
   })


   it("should not return partial updates for MCP tools and finalize returns McpToolUse", () => {
     const id = "mcp_stream_1"
     const name = "mcp--serverA--doThing"
     NativeToolCallParser.startStreamingToolCall(id, name)
   
     // For MCP dynamic tools, processStreamingChunk should not return partial updates
     const partial = NativeToolCallParser.processStreamingChunk(id, JSON.stringify({ foo: "bar" }))
     expect(partial).toBeNull()
   
     // Streaming call should still be active
     expect(NativeToolCallParser.hasActiveStreamingToolCalls()).toBe(true)
   
     // Finalize should parse into an McpToolUse and remove the streaming entry
     const final = NativeToolCallParser.finalizeStreamingToolCall(id)
     expect(final).not.toBeNull()
     if (final && (final as any).type === "mcp_tool_use") {
       expect((final as any).serverName).toBe("serverA")
       expect((final as any).toolName).toBe("doThing")
       // Original name (as returned) should preserve the original tool name string
       expect((final as any).name).toBe(name)
     } else {
       // Fail explicitly if not the expected type
       fail("Expected an McpToolUse result from finalizeStreamingToolCall")
     }
   
     // Ensure streaming state cleared
     expect(NativeToolCallParser.hasActiveStreamingToolCalls()).toBe(false)
   })


   it("should buffer deltas until name arrives and emit start/delta/end events", () => {
     // Ensure clean state
     NativeToolCallParser.clearRawChunkState()
   
     // First chunk: has id and arguments but no name -> should be buffered, no events
     let events = NativeToolCallParser.processRawChunk({ index: 10, id: "id1", arguments: "partial1" })
     expect(events).toEqual([])
   
     // Second chunk: same index, name is provided -> should emit start + flush buffered delta
     events = NativeToolCallParser.processRawChunk({ index: 10, name: "read_file" })
     expect(events).toHaveLength(2)
     expect(events[0]).toEqual({ type: "tool_call_start", id: "id1", name: "read_file" })
     expect(events[1]).toEqual({ type: "tool_call_delta", id: "id1", delta: "partial1" })
   
     // Third chunk: provide another argument delta -> should emit a delta immediately
     events = NativeToolCallParser.processRawChunk({ index: 10, arguments: "more" })
     expect(events).toHaveLength(1)
     expect(events[0]).toEqual({ type: "tool_call_delta", id: "id1", delta: "more" })
   
     // processFinishReason with "tool_calls" should emit an end event for tracked call
     const finishEvents = NativeToolCallParser.processFinishReason("tool_calls")
     expect(finishEvents).toEqual([{ type: "tool_call_end", id: "id1" }])
   
     // finalizeRawChunks should also emit end events for started tracked entries and then clear state
     const finalizeEvents = NativeToolCallParser.finalizeRawChunks()
     expect(finalizeEvents).toEqual([{ type: "tool_call_end", id: "id1" }])
   })

		})
	})
})
