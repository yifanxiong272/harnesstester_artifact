let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.repairToolUseResultPairing', function() {
    const fn = testpilot_subject.file_0003.repairToolUseResultPairing;

    it('passes through non-object messages (null, string) unchanged', function() {
        const messages = [
            null,
            "a simple string",
            { role: "user", content: "hello" }
        ];
        const res = fn(messages, {});
        // When nothing changes, the function returns the original array reference or identical content.
        assert.ok(res && typeof res === 'object', 'result should be an object');
        assert.ok(Array.isArray(res.messages), 'result.messages should be an array');
        assert.deepStrictEqual(res.messages, messages);
        assert.deepStrictEqual(res.added, [], 'no added entries expected');
        assert.strictEqual(res.droppedDuplicateCount, 0);
        assert.strictEqual(res.droppedOrphanCount, 0);
        assert.strictEqual(res.moved, false);
    });

    })