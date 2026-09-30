let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.extractToolResultId', function() {
        it('returns a falsy value when no toolResultId is present', function() {
            const msg = 'http://example.com/report?foo=1&bar=3';
            const result = testpilot_subject.file_0009.extractToolResultId(msg);
            // Accept null, undefined, empty string, or any other falsy "no id" result
            assert.ok(!result, 'Expected a falsy value when no toolResultId is present');
        });

            })
})