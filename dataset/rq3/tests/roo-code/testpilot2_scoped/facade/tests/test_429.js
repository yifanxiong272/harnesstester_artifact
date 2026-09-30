let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0020 &&
               testpilot_subject.file_0020.mergeEnvironmentDetailsForMiniMax;

    it('mergeEnvironmentDetailsForMiniMax should be a function', function() {
        assert.ok(fn, 'function is missing');
        assert.strictEqual(typeof fn, 'function');
    });

    })