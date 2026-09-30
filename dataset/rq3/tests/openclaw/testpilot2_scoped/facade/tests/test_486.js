let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0017.analyzeBootstrapBudget', function() {
        const fn = testpilot_subject && testpilot_subject.file_0017 && testpilot_subject.file_0017.analyzeBootstrapBudget;

        it('should export a function', function() {
            assert.strictEqual(typeof fn, 'function', 'analyzeBootstrapBudget should be a function');
        });

            })
})