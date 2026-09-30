let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('creates an assistant turn with a tool (toolUse) that is updated by a toolResult to status ok', function() {
        const messages = [
            {
                id: "a1",
                role: "assistant",
                // A single assistant message that contains a toolUse followed by its toolResult
                content: [
                    { type: "toolUse", toolCallId: "t1", toolName: "echo", input: "hi", outputLines: ["hi"] },
                    { type: "text", text: "I called a tool" },
                    { type: "toolResult", toolCallId: "t1", isError: false, output: ["hi"] }
                ],
                durationMs: 42
            }
        ];

        const approvals = [];
        // No getFileUrl needed here
        const turns = testpilot_subject.file_0005.messagesToTurns(messages, approvals, null);

        // Expect one assistant turn containing a tool that has been updated to ok
        assert.strictEqual(Array.isArray(turns), true);
        assert.strictEqual(turns.length, 1);
        const t = turns[0];
        assert.strictEqual(t.role, "assistant");
        assert.strictEqual(typeof t.tools, "object" || typeof t.tools, "tools should be present");
        assert.ok(Array.isArray(t.tools), "tools should be an array");
        assert.strictEqual(t.tools.length, 1);
        const tool = t.tools[0];
        assert.strictEqual(tool.id, "t1");
        // toolResult should have set status to "ok"
        assert.strictEqual(tool.status, "ok");
        // Blocks should include a tool block referencing the same id
        assert.ok(Array.isArray(t.blocks));
        const toolBlock = t.blocks.find(b => b.kind === "tool" && b.tool && b.tool.id === "t1");
        assert.ok(toolBlock, "should have a tool block for t1");
    });

    })