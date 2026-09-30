let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.PromptManager.prototype.beforePrompt', function() {
        const beforePrompt = testpilot_subject.file_0004.PromptManager.prototype.beforePrompt;

        it('calls onBeforePrompt when present', function() {
            let called = 0;
            const obj = {
                onBeforePrompt: function() {
                    called += 1;
                }
            };

            // invoke the prototype method with obj as this
            beforePrompt.call(obj);

            assert.strictEqual(called, 1, 'onBeforePrompt should be called exactly once');
        });

            })
})