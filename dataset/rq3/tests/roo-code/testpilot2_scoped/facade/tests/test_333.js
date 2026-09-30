let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0012.MessageQueueService.prototype.dispose', function() {

        it('clears the _messages array and calls removeAllListeners', function() {
            const svc = new testpilot_subject.file_0012.MessageQueueService();

            // populate messages and replace removeAllListeners with a spy
            svc._messages = [ 'a', 'b', 'c' ];
            let called = false;
            svc.removeAllListeners = function() { called = true; };

            svc.dispose();

            // _messages should be an empty array
            assert.ok(Array.isArray(svc._messages));
            assert.strictEqual(svc._messages.length, 0);

            // removeAllListeners should have been called
            assert.strictEqual(called, true);
        });

            })
})