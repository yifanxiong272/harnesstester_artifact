let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.extractObservedOverflowTokenCount', function() {
        it('returns no meaningful numeric result when the message contains no number', function() {
            const fn = testpilot_subject.file_0001.extractObservedOverflowTokenCount;
            const msg = 'No overflow observed in this run.';
            const result = fn(msg);
            // Accept several reasonable "no result" representations:
            // null, undefined, NaN, empty string, or false.
            const isNoResult = result === null
                || result === undefined
                || (typeof result === 'number' && Number.isNaN(result))
                || (typeof result === 'string' && result.trim() === '')
                || result === false;
            assert.ok(isNoResult, 'Expected a non-numeric/no-result value when no number is present');
        });
    });
});