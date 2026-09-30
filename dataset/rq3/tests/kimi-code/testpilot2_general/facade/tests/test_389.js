let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WsConnection.prototype.onTerminalResize - is a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0006, "expected file_0006 to exist on module");
        const onTerminalResize = testpilot_subject.file_0006.WsConnection.prototype.onTerminalResize;
        assert.strictEqual(typeof onTerminalResize, 'function', 'onTerminalResize should be a function');
    });

    })