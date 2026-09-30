let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0013.resolveExecDetail;

    it('should return undefined when called with no arguments', function() {
        assert.strictEqual(fn(), undefined);
    });

    })