let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0009 &&
               testpilot_subject.file_0009.normalizeNotifyOutput;

    it('exports normalizeNotifyOutput as a function', function() {
        assert.strictEqual(typeof fn, 'function');
    });

    })