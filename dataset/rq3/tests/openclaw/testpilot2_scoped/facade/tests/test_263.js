let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const normalize = testpilot_subject.file_0008.normalizeNotifyOutput;

    it('normalizeNotifyOutput should exist and be a function', function() {
        assert.ok(normalize, 'normalizeNotifyOutput is missing');
        assert.strictEqual(typeof normalize, 'function', 'normalizeNotifyOutput should be a function');
    });

    })