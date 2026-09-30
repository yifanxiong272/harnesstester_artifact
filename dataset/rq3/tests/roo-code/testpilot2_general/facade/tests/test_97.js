let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const outputMessage = testpilot_subject.file_0002.OutputManager.prototype.outputMessage;

    it('calls outputSayMessage with correct arguments (default skipFirstUserMessage=true)', function(done) {
        // Prepare a "this" object with required pieces
        const obj = {
            displayedMessages: new Map(), // no previous display
        };

        // Spy for outputSayMessage
        let called = 0;
        let capturedArgs = null;
        obj.outputSayMessage = function(ts, say, text, isPartial, alreadyDisplayedComplete, skipFirstUserMessage) {
            called++;
            capturedArgs = { ts, say, text, isPartial, alreadyDisplayedComplete, skipFirstUserMessage };
        };
        // Also ensure outputCommandOutput is present but should not be called
        obj.outputCommandOutput = function() {
            throw new Error('outputCommandOutput should not be called in this test');
        };

        // Message triggering the "say" branch
        const msg = { ts: 't1', type: 'say', say: 'agent', text: 'hello', partial: false };

        // Call the method under test without providing skipFirstUserMessage (defaults to true)
        outputMessage.call(obj, msg);

        assert.strictEqual(called, 1, 'outputSayMessage should be called once');
        // The implementation may not pass an explicit alreadyDisplayedComplete value (it's undefined),
        // so expect undefined here to match actual behavior.
        assert.deepStrictEqual(capturedArgs, {
            ts: 't1',
            say: 'agent',
            text: 'hello',
            isPartial: false,
            alreadyDisplayedComplete: undefined,
            skipFirstUserMessage: true
        });

        done();
    });

    })