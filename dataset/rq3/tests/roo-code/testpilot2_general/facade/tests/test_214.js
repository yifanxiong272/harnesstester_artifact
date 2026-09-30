let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0005.initializeSourceMaps', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0005, 'testpilot_subject.file_0005 is expected to exist');
            assert.strictEqual(typeof testpilot_subject.file_0005.initializeSourceMaps, 'function',
                'initializeSourceMaps should be a function');
        });

            })
})