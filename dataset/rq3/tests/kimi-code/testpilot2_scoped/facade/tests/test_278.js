let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.clearContext', function() {
        const fn = testpilot_subject.file_0002.KimiCore && testpilot_subject.file_0002.KimiCore.prototype && testpilot_subject.file_0002.KimiCore.prototype.clearContext;
        it('should exist as a function on the prototype', function() {
            assert.strictEqual(typeof fn, 'function', 'clearContext should be a function on the prototype');
        });

            })
})