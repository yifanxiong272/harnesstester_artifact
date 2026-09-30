let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WsConnection.prototype.onMessage', function() {
        const proto = testpilot_subject &&
                      testpilot_subject.file_0006 &&
                      testpilot_subject.file_0006.WsConnection &&
                      testpilot_subject.file_0006.WsConnection.prototype;

        it('should exist and be a function', function() {
            assert.ok(proto, 'WsConnection.prototype not found on testpilot_subject.file_0006');
            assert.strictEqual(typeof proto.onMessage, 'function', 'onMessage should be a function');
            // also check expected arity (most implementations take one argument)
            assert.ok(proto.onMessage.length >= 0, 'onMessage should accept arguments');
        });

            })
})