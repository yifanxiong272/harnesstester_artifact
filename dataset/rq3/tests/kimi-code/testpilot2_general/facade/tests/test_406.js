let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WsConnection.prototype.subscribe', function() {
        it('should exist and be a function with arity 1', function() {
            assert.ok(testpilot_subject, 'testpilot_subject should be importable');
            assert.ok(testpilot_subject.file_0006, 'file_0006 should exist on module');
            assert.ok(testpilot_subject.file_0006.WsConnection, 'WsConnection should exist on file_0006');
            const subscribe = testpilot_subject.file_0006.WsConnection.prototype.subscribe;
            assert.strictEqual(typeof subscribe, 'function', 'subscribe should be a function');
            // Expect one declared parameter name (sid)
            assert.strictEqual(subscribe.length, 1, 'subscribe should declare one parameter (sid)');
        });

            })
})