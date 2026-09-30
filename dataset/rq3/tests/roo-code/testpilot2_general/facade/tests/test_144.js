let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.OutputManager.prototype.outputSayMessage', function() {
        it('calls outputTextMessage with correct arguments (including skipFirstUserMessage)', function() {
            const OM = new testpilot_subject.file_0002.OutputManager();

            // ensure displayedMessages exists in case constructor doesn't create it
            if (!OM.displayedMessages) OM.displayedMessages = new Map();

            let called = false;
            let capturedArgs = null;
            OM.outputTextMessage = function(ts, text, isPartial, alreadyDisplayedComplete, skipFirstUserMessage) {
                called = true;
                capturedArgs = { ts, text, isPartial, alreadyDisplayedComplete, skipFirstUserMessage };
            };

            const ts = 1001;
            OM.outputSayMessage(ts, "text", "hello world", true, false, /*skipFirstUserMessage=*/ true);

            assert.strictEqual(called, true, "outputTextMessage should have been called");
            assert.deepStrictEqual(capturedArgs, {
                ts: ts,
                text: "hello world",
                isPartial: true,
                alreadyDisplayedComplete: false,
                skipFirstUserMessage: true
            });
        });

            })
})