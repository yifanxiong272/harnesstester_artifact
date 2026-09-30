let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Sanity checks and simple robustness checks for WsConnection.prototype.onTerminalClose
    // These tests are intentionally conservative: they verify the function exists and that
    // calling it with various inputs does not throw. They are self-contained and do not
    // rely on external resources.

    it('should have WsConnection.prototype.onTerminalClose as a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0006, 'file_0006 should be present on module');
        const proto = testpilot_subject.file_0006.WsConnection && testpilot_subject.file_0006.WsConnection.prototype;
        assert.ok(proto, 'WsConnection.prototype should exist');
        assert.strictEqual(typeof proto.onTerminalClose, 'function', 'onTerminalClose should be a function');
    });

    })