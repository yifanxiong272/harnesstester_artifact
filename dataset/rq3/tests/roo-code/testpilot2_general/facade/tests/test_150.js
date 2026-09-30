let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('partial output: should call streamContent and mark displayedMessages as partial', function() {
        const OutputManager = testpilot_subject.file_0002.OutputManager;
        const mgr = new OutputManager();

        // Ensure maps exist and are fresh
        mgr.displayedMessages = new Map();
        mgr.streamedContent = new Map();

        const calls = [];
        mgr.streamContent = function(ts, text, header) {
            calls.push({fn: 'streamContent', ts, text, header});
        };
        mgr.writeRaw = function() { throw new Error('writeRaw should not be called for partial'); };
        mgr.finishStream = function() { throw new Error('finishStream should not be called for partial'); };

        const ts = 123;
        const text = "partial-text";

        mgr.outputCommandOutput(ts, text, true, false);

        // Verify streamContent was called once with expected args
        assert.strictEqual(calls.length, 1, 'streamContent should be called once');
        assert.deepStrictEqual(calls[0], {fn: 'streamContent', ts, text, header: "[command output]"});

        // displayedMessages should have entry with partial: true
        const msg = mgr.displayedMessages.get(ts);
        assert.ok(msg, 'displayedMessages should have an entry for ts');
        assert.deepStrictEqual(msg, {ts, text, partial: true});
    });

    })