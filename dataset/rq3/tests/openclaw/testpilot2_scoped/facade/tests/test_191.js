let mocha = require('mocha');
let assert = require('assert');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0007.applyPatch basic behavior', function() {

        it('should export applyPatch as a callable function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0007, 'file_0007 namespace should exist');
            assert.strictEqual(typeof testpilot_subject.file_0007.applyPatch, 'function', 'applyPatch should be a function');
        });

            })
})