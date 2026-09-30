let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0002.OutputManager basic behavior', function() {
        it('exports file_0002.OutputManager as a constructible function', function() {
            assert.ok(testpilot_subject, 'module testpilot_subject should be present');
            assert.ok(testpilot_subject.file_0002, 'module should have file_0002 namespace');
            assert.strictEqual(typeof testpilot_subject.file_0002.OutputManager, 'function', 'OutputManager should be a function (constructor)');
        });

            })
})