let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0019.createUsageNormalizer', function() {
        it('should return a function when given a function', function() {
            function dummy() {}
            const normalizer = testpilot_subject.file_0019.createUsageNormalizer(dummy);
            assert.strictEqual(typeof normalizer, 'function');
        });

            })
})