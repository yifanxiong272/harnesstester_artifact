let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.getApiErrorPayloadFingerprint;

    it('returns null for falsy raw inputs', function() {
        // According to implementation, if (!raw) -> return null
        assert.strictEqual(fn(undefined), null, 'undefined should yield null');
        assert.strictEqual(fn(null), null, 'null should yield null');
        assert.strictEqual(fn(''), null, 'empty string should yield null');
        assert.strictEqual(fn(0), null, '0 should yield null');
        assert.strictEqual(fn(false), null, 'false should yield null');
    });

    })