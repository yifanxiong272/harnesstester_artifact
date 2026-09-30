let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0017.buildBootstrapTruncationSignature', function() {
        it('returns undefined when analysis.hasTruncation is falsy', function() {
            const analysis = { hasTruncation: false };
            const result = testpilot_subject.file_0017.buildBootstrapTruncationSignature(analysis);
            assert.strictEqual(result, undefined);
        });

            })
})