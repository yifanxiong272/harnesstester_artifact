let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should send terminal-not-found ack and not call logger.warn for TerminalNotFoundError', function() {
        // Create a connection-like object that uses the prototype method without running any constructor logic
        let proto = testpilot_subject.file_0006.WsConnection.prototype;
        let conn = Object.create(proto);

        // Spies to capture calls
        let sent = [];
        let warns = [];

        conn.send = function(arg) { sent.push(arg); };
        conn.logger = { warn: function(obj, fallback) { warns.push([obj, fallback]); } };

        // Error object with matching name
        let err = { name: "TerminalNotFoundError", message: "no terminal" };

        // Call the method under test
        proto.sendTerminalErrorAck.call(conn, "ID-1", err, "fallback text");

        // Expectations
        assert.strictEqual(sent.length, 1, "send should be called exactly once");
        assert.strictEqual(warns.length, 0, "logger.warn should not be called for TerminalNotFoundError");

        // The implementation uses the message "terminal not found" when building the ack,
        // so the serialized ack payload should contain that phrase.
        let serialized = JSON.stringify(sent[0]).toLowerCase();
        assert.ok(serialized.includes("terminal not found"), "ack payload should mention 'terminal not found'");
    });

    })