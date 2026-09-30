let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.parseApiErrorInfo', function() {
    const parse = testpilot_subject.file_0001.parseApiErrorInfo;

    it('returns null for null/undefined/blank input', function() {
        assert.strictEqual(parse(null), null, 'null should return null');
        assert.strictEqual(parse(undefined), null, 'undefined should return null');
        assert.strictEqual(parse('   '), null, 'blank-only string should return null');
    });

    })