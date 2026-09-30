let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0014.filterToolResultMediaUrls', function() {
        it('should return an array and handle empty mediaUrls', function(done) {
            let toolName = 'anyTool';
            let mediaUrls = [];
            let result = {};
            let out = testpilot_subject.file_0014.filterToolResultMediaUrls(toolName, mediaUrls, result);
            assert.ok(Array.isArray(out), 'expected result to be an array');
            assert.strictEqual(out.length, 0, 'expected empty input to produce empty output');
            done();
        });

            })
})