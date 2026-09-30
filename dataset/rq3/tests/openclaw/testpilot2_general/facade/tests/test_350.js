let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0011.parseBrowserMajorVersion', function() {
        it('parses typical chrome-style version strings into major integers', function() {
            // Typical full version
            assert.strictEqual(testpilot_subject.file_0011.parseBrowserMajorVersion("106.0.5249.0"), 106);
            // Short dotted version
            assert.strictEqual(testpilot_subject.file_0011.parseBrowserMajorVersion("7.1"), 7);
            // Leading zeros should be handled by parseInt
            assert.strictEqual(testpilot_subject.file_0011.parseBrowserMajorVersion("0010.5"), 10);
            // Zero major version
            assert.strictEqual(testpilot_subject.file_0011.parseBrowserMajorVersion("0.0.0"), 0);
        });

            })
})