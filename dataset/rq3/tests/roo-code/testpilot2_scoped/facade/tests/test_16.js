let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const extract = testpilot_subject.file_0004.extractCommandBlocks;

    it('returns empty string when content is neither string nor array', function(done) {
        const message = { content: 12345 };
        const result = extract(message);
        assert.strictEqual(result, "", "Expected empty string for non-string/non-array content");
        done();
    });

    })