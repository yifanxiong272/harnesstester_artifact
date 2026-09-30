let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0014.extractToolResultText - handles null and undefined without throwing', function() {
        let outNull = testpilot_subject.file_0014.extractToolResultText(null);
        let outUndef = testpilot_subject.file_0014.extractToolResultText(undefined);
        // Should not throw and should return either a string or undefined in both cases.
        assert.ok(['string', 'undefined'].includes(typeof outNull));
        assert.ok(['string', 'undefined'].includes(typeof outUndef));
    });
});