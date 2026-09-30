let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.fetchFirecrawlContent', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject, 'testpilot_subject should be defined');
            assert.ok(testpilot_subject.file_0006, 'testpilot_subject.file_0006 should be defined');
            assert.ok(
                typeof testpilot_subject.file_0006.fetchFirecrawlContent === 'function',
                'fetchFirecrawlContent should be a function'
            );
        });

            })
})