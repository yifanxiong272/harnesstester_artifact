let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.OutputManager.prototype.outputCompletionResult', function() {
        // Helper to create a minimal OutputManager-like object that uses the real prototype
        function makeOutputManager() {
            // Create an object whose prototype is the real prototype so we exercise the real method
            let om = Object.create(testpilot_subject.file_0002.OutputManager.prototype);
            om.displayedMessages = new Map();
            om.completionResultStreamed = false;
            om._outputCalls = [];
            om.output = function() {
                // record the arguments array for each call
                om._outputCalls.push(Array.from(arguments));
            };
            return om;
        }

        it('when completionResultStreamed === true and no previous display, outputs only label and stores text', function() {
            let om = makeOutputManager();
            om.completionResultStreamed = true;
            const ts = 'ts1';
            const text = 'some result text';

            // Call the actual method from the prototype
            om.outputCompletionResult(ts, text);

            // One output call, with only the label arg
            assert.strictEqual(om._outputCalls.length, 1, 'expected one output call');
            assert.deepStrictEqual(om._outputCalls[0], ["\n[task complete]"]);

            // displayedMessages should have an entry for ts with partial:false and text preserved
            assert.strictEqual(om.displayedMessages.has(ts), true);
            const entry = om.displayedMessages.get(ts);
            assert.strictEqual(entry.ts, ts);
            assert.strictEqual(entry.partial, false);
            assert.strictEqual(entry.text, text);
        });

            })
})