let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0019.createUsageNormalizer - returns undefined for falsy usage', function(done) {
        const normalizer = testpilot_subject.file_0019.createUsageNormalizer();
        assert.strictEqual(normalizer(null), undefined);
        assert.strictEqual(normalizer(undefined), undefined);
        assert.strictEqual(normalizer(false), undefined); // any falsy -> undefined per implementation
        done();
    });

    })