let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('has formatResult on the CacheStrategy prototype', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0010);
        assert.ok(testpilot_subject.file_0010.CacheStrategy);
        assert.strictEqual(typeof testpilot_subject.file_0010.CacheStrategy.prototype.formatResult, 'function');
    });

    })