let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let fs = require('fs');
let os = require('os');
let path = require('path');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.FsSearchService.prototype.grep', function() {
        it('should exist and be an async function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0002, 'module should expose file_0002');
            const grep = testpilot_subject.file_0002.FsSearchService.prototype.grep;
            assert.strictEqual(typeof grep, 'function', 'grep should be a function');
            // Async functions have constructor name "AsyncFunction"
            assert.strictEqual(grep.constructor && grep.constructor.name, 'AsyncFunction', 'grep should be an async function');
        });

            })
})