let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0017.resolveBootstrapWarningSignaturesSeen', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0017 &&
               testpilot_subject.file_0017.resolveBootstrapWarningSignaturesSeen;

    it('should be exported as a function', function() {
        assert.strictEqual(typeof fn, 'function',
            'resolveBootstrapWarningSignaturesSeen should be a function');
    });

    })