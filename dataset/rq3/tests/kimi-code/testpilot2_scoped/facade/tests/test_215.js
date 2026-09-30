let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0002.KimiCore.prototype.setThinking', function() {
        it('module exposes file_0002 and KimiCore', function() {
            assert.ok(testpilot_subject, 'testpilot_subject should be defined');
            assert.ok(
                testpilot_subject.file_0002,
                'testpilot_subject.file_0002 should be defined'
            );
            assert.ok(
                testpilot_subject.file_0002.KimiCore,
                'testpilot_subject.file_0002.KimiCore should be defined'
            );
        });

            })
})