let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.repairToolUseResultPairing', function() {
    const fn = testpilot_subject.file_0003.repairToolUseResultPairing;

    it('drops top-level orphan toolResult messages', function() {
        const msgs = [
            { role: 'toolResult', some: 'data' }
        ];
        const res = fn(msgs, {});
        // orphan toolResult should be dropped
        assert.strictEqual(Array.isArray(res.messages), true);
        assert.strictEqual(res.messages.length, 0, 'expected no messages after dropping orphan toolResult');
        assert.strictEqual(res.added.length, 0, 'no added tool results expected');
        assert.strictEqual(res.droppedOrphanCount >= 1, true, 'expected at least one dropped orphan');
        // function signals change via moved (return.moved is set to changedOrMoved)
        assert.strictEqual(res.moved, true);
    });

    })