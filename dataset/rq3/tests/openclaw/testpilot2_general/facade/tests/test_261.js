let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const normalize = testpilot_subject.file_0009.normalizePathPrepend;

    it('normalizePathPrepend should be a function', function(done) {
        assert.strictEqual(typeof normalize, 'function');
        done();
    });

    })