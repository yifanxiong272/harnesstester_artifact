let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.OutputManager.prototype.outputCompletionSayMessage', function() {
        it('should not throw for a normal final message', function() {
            const mgr = new testpilot_subject.file_0002.OutputManager();
            assert.doesNotThrow(() => {
                mgr.outputCompletionSayMessage(Date.now(), 'Hello world', false, false);
            });
        });

            })
})