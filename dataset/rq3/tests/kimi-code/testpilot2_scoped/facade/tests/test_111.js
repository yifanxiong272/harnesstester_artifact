let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.archiveSession', function() {
        // get the function under test
        const archiveSession = testpilot_subject &&
            testpilot_subject.file_0002 &&
            testpilot_subject.file_0002.KimiCore &&
            testpilot_subject.file_0002.KimiCore.prototype &&
            testpilot_subject.file_0002.KimiCore.prototype.archiveSession;

        it('should be defined as an async function', function() {
            assert.ok(archiveSession, 'archiveSession is not defined');
            // It should be an async function (its constructor name is "AsyncFunction")
            assert.strictEqual(archiveSession.constructor.name, 'AsyncFunction');
        });

            })
})