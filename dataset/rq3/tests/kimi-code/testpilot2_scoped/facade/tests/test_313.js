let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.listMcpServers', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0002, 'file_0002 namespace missing');
            assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore missing');
            assert.strictEqual(typeof testpilot_subject.file_0002.KimiCore.prototype.listMcpServers, 'function');
        });

            })
})