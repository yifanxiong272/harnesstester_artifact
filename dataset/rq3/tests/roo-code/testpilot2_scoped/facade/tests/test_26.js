let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject && testpilot_subject.file_0004 && testpilot_subject.file_0004.toolResultToText;

    it('exports a function', function() {
        assert.strictEqual(typeof fn, 'function', 'toolResultToText should be a function');
    });

    })