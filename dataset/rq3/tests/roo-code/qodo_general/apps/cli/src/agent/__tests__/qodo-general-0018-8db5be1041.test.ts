import type { ClineMessage } from "@roo-code/types"
import { Writable } from "stream"

import { JsonEventEmitter } from "../json-event-emitter.js"

function createMockStdout(): { stdout: NodeJS.WriteStream; lines: () => Record<string, unknown>[] } {
	const chunks: string[] = []

	const writable = new Writable({
		write(chunk, _encoding, callback) {
			chunks.push(chunk.toString())
			callback()
		},
	}) as unknown as NodeJS.WriteStream

	const lines = () =>
		chunks
			.join("")
			.split("\n")
			.filter((line) => line.length > 0)
			.map((line) => JSON.parse(line) as Record<string, unknown>)

	return { stdout: writable, lines }
}

function emitMessage(emitter: JsonEventEmitter, message: ClineMessage): void {
	;(emitter as unknown as { handleMessage: (msg: ClineMessage, isUpdate: boolean) => void }).handleMessage(
		message,
		false,
	)
}

function createAskMessage(overrides: Partial<ClineMessage>): ClineMessage {
	return {
		ts: 1,
		type: "ask",
		ask: "tool",
		partial: true,
		text: "",
		...overrides,
	} as ClineMessage
}

describe("JsonEventEmitter streaming deltas", () => {
	it("streams ask:command partial updates as deltas and emits full final snapshot", () => {
		const { stdout, lines } = createMockStdout()
		const emitter = new JsonEventEmitter({ mode: "stream-json", stdout })
		const id = 101

		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "command",
				partial: true,
				text: "g",
			}),
		)
		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "command",
				partial: true,
				text: "gh",
			}),
		)
		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "command",
				partial: true,
				text: "gh pr",
			}),
		)
		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "command",
				partial: false,
				text: "gh pr",
			}),
		)

		const output = lines()
		expect(output).toHaveLength(4)
		expect(output[0]).toMatchObject({
			type: "tool_use",
			id,
			subtype: "command",
			content: "g",
			tool_use: { name: "execute_command", input: { command: "g" } },
		})
		expect(output[1]).toMatchObject({
			type: "tool_use",
			id,
			subtype: "command",
			content: "h",
			tool_use: { name: "execute_command", input: { command: "h" } },
		})
		expect(output[2]).toMatchObject({
			type: "tool_use",
			id,
			subtype: "command",
			content: " pr",
			tool_use: { name: "execute_command", input: { command: " pr" } },
		})
		expect(output[3]).toMatchObject({
			type: "tool_use",
			id,
			subtype: "command",
			tool_use: { name: "execute_command", input: { command: "gh pr" } },
			done: true,
		})
		expect(output[3]).not.toHaveProperty("content")
	})

	it("streams ask:tool snapshots as structured deltas and preserves full final payload", () => {
		const { stdout, lines } = createMockStdout()
		const emitter = new JsonEventEmitter({ mode: "stream-json", stdout })
		const id = 202
		const first = JSON.stringify({ tool: "readFile", path: "a" })
		const second = JSON.stringify({ tool: "readFile", path: "ab" })

		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "tool",
				partial: true,
				text: first,
			}),
		)
		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "tool",
				partial: true,
				text: second,
			}),
		)
		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "tool",
				partial: false,
				text: second,
			}),
		)

		const output = lines()
		expect(output).toHaveLength(3)
		expect(output[0]).toMatchObject({
			type: "tool_use",
			id,
			subtype: "tool",
			content: first,
			tool_use: { name: "readFile" },
		})
		expect(output[1]).toMatchObject({
			type: "tool_use",
			id,
			subtype: "tool",
			content: "b",
			tool_use: { name: "readFile" },
		})
		expect(output[2]).toMatchObject({
			type: "tool_use",
			id,
			subtype: "tool",
			tool_use: { name: "readFile", input: { tool: "readFile", path: "ab" } },
			done: true,
		})
	})

	it("suppresses duplicate partial tool snapshots with no delta", () => {
		const { stdout, lines } = createMockStdout()
		const emitter = new JsonEventEmitter({ mode: "stream-json", stdout })
		const id = 303

		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "command",
				partial: true,
				text: "gh",
			}),
		)
		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "command",
				partial: true,
				text: "gh",
			}),
		)
		emitMessage(
			emitter,
			createAskMessage({
				ts: id,
				ask: "command",
				partial: true,
				text: "gh pr",
			}),
		)

		const output = lines()
		expect(output).toHaveLength(2)
		expect(output[0]).toMatchObject({ content: "gh" })
		expect(output[1]).toMatchObject({ content: " pr" })
	})

	it("streams say:command_output as deltas and correlates tool_result id to execute_command", () => {
		const { stdout, lines } = createMockStdout()
		const emitter = new JsonEventEmitter({ mode: "stream-json", stdout })
		const commandId = 404
		const outputTs = 405

		emitMessage(
			emitter,
			createAskMessage({
				ts: commandId,
				ask: "command",
				partial: false,
				text: "echo hello",
			}),
		)

		emitMessage(emitter, {
			ts: outputTs,
			type: "say",
			say: "command_output",
			partial: true,
			text: "line1\n",
		} as ClineMessage)
		emitMessage(emitter, {
			ts: outputTs,
			type: "say",
			say: "command_output",
			partial: true,
			text: "line1\nline2\n",
		} as ClineMessage)
		emitMessage(emitter, {
			ts: outputTs,
			type: "say",
			say: "command_output",
			partial: false,
			text: "line1\nline2\n",
		} as ClineMessage)

		const output = lines()
		expect(output).toHaveLength(4)
		expect(output[0]).toMatchObject({
			type: "tool_use",
			id: commandId,
			subtype: "command",
			tool_use: { name: "execute_command", input: { command: "echo hello" } },
			done: true,
		})
		expect(output[1]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command", output: "line1\n" },
		})
		expect(output[2]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command", output: "line2\n" },
		})
		expect(output[3]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command" },
			done: true,
		})
		expect(output[3]).not.toHaveProperty("tool_result.output")
	})

	it("prefers status-driven command output streaming and suppresses duplicate say completion", () => {
		const { stdout, lines } = createMockStdout()
		const emitter = new JsonEventEmitter({ mode: "stream-json", stdout })
		const commandId = 505

		emitMessage(
			emitter,
			createAskMessage({
				ts: commandId,
				ask: "command",
				partial: false,
				text: "echo streamed",
			}),
		)

		emitter.emitCommandOutputChunk("line1\n")
		emitter.emitCommandOutputChunk("line1\nline2\n")
		emitter.markCommandOutputExited(17)

		// This completion say is expected from the extension and should finalize
		// the status-driven command_output stream without duplicating content.
		emitMessage(emitter, {
			ts: 999,
			type: "say",
			say: "command_output",
			partial: false,
			text: "line1\nline2\n",
		} as ClineMessage)

		const output = lines()
		expect(output).toHaveLength(4)
		expect(output[0]).toMatchObject({
			type: "tool_use",
			id: commandId,
			subtype: "command",
			tool_use: { name: "execute_command", input: { command: "echo streamed" } },
			done: true,
		})
		expect(output[1]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command", output: "line1\n" },
		})
		expect(output[2]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command", output: "line2\n" },
		})
		expect(output[3]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command", exitCode: 17 },
			done: true,
		})
	})

	it("flushes remaining output on final say completion after fast status:exited", () => {
		const { stdout, lines } = createMockStdout()
		const emitter = new JsonEventEmitter({ mode: "stream-json", stdout })
		const commandId = 606

		emitMessage(
			emitter,
			createAskMessage({
				ts: commandId,
				ask: "command",
				partial: false,
				text: "aws sts get-caller-identity",
			}),
		)

		emitter.emitCommandOutputChunk("{\n")
		emitter.markCommandOutputExited(0)

		emitMessage(emitter, {
			ts: 607,
			type: "say",
			say: "command_output",
			partial: false,
			text: '{\n  "Account": "123"\n}\n',
		} as ClineMessage)

		const output = lines()
		expect(output).toHaveLength(3)
		expect(output[1]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command", output: "{\n" },
		})
		expect(output[2]).toMatchObject({
			type: "tool_result",
			id: commandId,
			subtype: "command",
			tool_result: { name: "execute_command", output: '  "Account": "123"\n}\n', exitCode: 0 },
			done: true,
		})
	})

 it("attachToClient_emits_init_and_detach_unsubscribes", () => {
   const { stdout, lines } = createMockStdout()
 
   // Simple mock ExtensionClient that stores listeners and returns unsub functions
   const listeners: Record<string, Function[]> = {}
   const unsubFlags: Record<string, boolean> = {
     message: false,
     messageUpdated: false,
     stateChange: false,
     taskCompleted: false,
     error: false,
   }
 
   const client = {
     on(event: string, cb: Function) {
       listeners[event] = listeners[event] || []
       listeners[event].push(cb)
       return () => {
         // mark that the unsub for this event was called
         // ensure we only set known keys to avoid TS complaining
         if (Object.prototype.hasOwnProperty.call(unsubFlags, event)) {
           unsubFlags[event as keyof typeof unsubFlags] = true
         }
       }
     },
     emit(event: string, payload?: any) {
       for (const cb of listeners[event] || []) {
         // invoke as the real client would: with the payload
         cb(payload)
       }
     },
   } as unknown as any
 
   const emitter = new JsonEventEmitter({
     mode: "stream-json",
     stdout,
     schemaVersion: 2,
     protocol: "test-proto",
     capabilities: ["a", "b"],
   })
 
   emitter.attachToClient(client as any)
 
   // The attach should immediately emit a system:init event
   const out1 = lines()
   expect(out1).toHaveLength(1)
   expect(out1[0]).toMatchObject({
     type: "system",
     subtype: "init",
     schemaVersion: 2,
     protocol: "test-proto",
     capabilities: ["a", "b"],
   })
 
   // Emit a message with a say type that is in SKIP_SAY_TYPES and ensure no new event is emitted
   client.emit("message", {
     ts: 123,
     type: "say",
     say: "api_req_deleted",
     partial: false,
     text: "ignored",
   } as ClineMessage)
 
   // still only the init line should be present
   const out2 = lines()
   expect(out2).toHaveLength(1)
 
   // Now detach and ensure each unsub was invoked
   emitter.detach()
   expect(unsubFlags.message).toBe(true)
   expect(unsubFlags.messageUpdated).toBe(true)
   expect(unsubFlags.stateChange).toBe(true)
   expect(unsubFlags.taskCompleted).toBe(true)
   expect(unsubFlags.error).toBe(true)
 })


 it("emitControl_and_emitQueue_include_requestId_and_done_flag", () => {
   const { stdout, lines } = createMockStdout()
   const emitter = new JsonEventEmitter({
     mode: "stream-json",
     stdout,
     requestIdProvider: () => "r1",
   })
 
   // Emit ack without explicit requestId -> requestIdProvider should supply "r1"
   emitter.emitControl({ subtype: "ack", command: { name: "cmd-ack" } })
 
   // Emit done with explicit requestId, success flag and command
   emitter.emitControl({
     subtype: "done",
     requestId: "explicit-req",
     command: { name: "cmd-done" },
     success: true,
   })
 
   // Emit a queue snapshot event
   emitter.emitQueue({
     subtype: "snapshot",
     taskId: "task-1",
     content: "snapshot",
     queueDepth: 2,
     queue: [{ taskId: "task-1", content: "c" }],
   })
 
   const out = lines()
   expect(out).toHaveLength(3)
 
   expect(out[0]).toMatchObject({
     type: "control",
     subtype: "ack",
     requestId: "r1",
     command: { name: "cmd-ack" },
   })
 
   expect(out[1]).toMatchObject({
     type: "control",
     subtype: "done",
     requestId: "explicit-req",
     command: { name: "cmd-done" },
     success: true,
     done: true,
   })
 
   expect(out[2]).toMatchObject({
     type: "queue",
     subtype: "snapshot",
     taskId: "task-1",
     content: "snapshot",
     queueDepth: 2,
     queue: [{ taskId: "task-1", content: "c" }],
   })
 })


 it("emits result event including parsed api_req_started cost", () => {
   const { stdout } = createMockStdout()
   const emitter = new JsonEventEmitter({ mode: "stream-json", stdout })
 
   // Emit an api_req_started say message with a JSON payload that includes cost/tokens
   const apiReqText = JSON.stringify({
     cost: 12.34,
     tokensIn: 10,
     tokensOut: 20,
     cacheWrites: 1,
     cacheReads: 2,
   })
   emitMessage(emitter, {
     ts: 1111,
     type: "say",
     say: "api_req_started",
     partial: false,
     text: apiReqText,
   } as ClineMessage)
 
   // Trigger task completion; handleTaskCompleted should include the lastCost parsed above
   ;(emitter as unknown as { handleTaskCompleted: (e: any) => void }).handleTaskCompleted({
     success: true,
     message: undefined,
   })
 
   const events = emitter.getEvents()
   // Find the result event
   const result = events.find((e) => e.type === "result")
   expect(result).toBeDefined()
   expect(result).toHaveProperty("cost")
   expect(result!.cost).toMatchObject({
     totalCost: 12.34,
     inputTokens: 10,
     outputTokens: 20,
     cacheWrites: 1,
     cacheReads: 2,
   })
 })

})
