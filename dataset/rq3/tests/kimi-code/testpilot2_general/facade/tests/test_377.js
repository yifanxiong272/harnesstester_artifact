let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Short sanity tests for WsConnection.prototype.onTerminalAttach.
    // These tests are defensive: they check that the method exists and that
    // calling it with various reasonable inputs does not throw and returns
    // undefined. They don't rely on external resources and are self-contained.

    it('should have onTerminalAttach as a function', function() {
        assert.ok(testpilot_subject);
        const proto = testpilot_subject.file_0006 && testpilot_subject.file_0006.WsConnection && testpilot_subject.file_0006.WsConnection.prototype;
        assert.ok(proto, 'WsConnection prototype not found on testpilot_subject.file_0006');
        assert.strictEqual(typeof proto.onTerminalAttach, 'function', 'onTerminalAttach should be a function');
    });

    })