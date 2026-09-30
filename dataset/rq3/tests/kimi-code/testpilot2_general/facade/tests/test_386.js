let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0006.WsConnection.prototype.onTerminalInput', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject.file_0006, 'file_0006 namespace missing');
            assert.ok(testpilot_subject.file_0006.WsConnection, 'WsConnection missing');
            assert.strictEqual(
                typeof testpilot_subject.file_0006.WsConnection.prototype.onTerminalInput,
                'function',
                'onTerminalInput should be a function'
            );
        });

            })
})