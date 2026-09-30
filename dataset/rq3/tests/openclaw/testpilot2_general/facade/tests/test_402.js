let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0014.extractToolResultMediaPaths', function() {
        it('is a function', function() {
            assert.ok(testpilot_subject);
            assert.strictEqual(typeof testpilot_subject.file_0014.extractToolResultMediaPaths, 'function');
        });

            })
})