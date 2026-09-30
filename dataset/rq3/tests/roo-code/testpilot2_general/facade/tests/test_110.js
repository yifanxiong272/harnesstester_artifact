let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.OutputManager.prototype.isAlreadyDisplayed', function() {
        it('should export OutputManager and the method should exist', function() {
            assert.ok(testpilot_subject.file_0002, 'file_0002 should be present on module');
            const OutputManager = testpilot_subject.file_0002.OutputManager;
            assert.ok(OutputManager, 'OutputManager should be exported');
            const om = new OutputManager();
            assert.strictEqual(typeof om.isAlreadyDisplayed, 'function', 'isAlreadyDisplayed should be a function');
        });

            })
})