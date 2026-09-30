let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.getApiErrorPayloadFingerprint', function() {
    const fn = testpilot_subject.file_0001.getApiErrorPayloadFingerprint;

    it('returns null for falsy raw values (null, undefined, empty string)', function() {
        assert.strictEqual(fn(null), null, 'null should produce null');
        assert.strictEqual(fn(undefined), null, 'undefined should produce null');
        // empty string is falsy and should be short-circuited by the function
        assert.strictEqual(fn(''), null, 'empty string should produce null');
    });

    })