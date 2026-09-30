let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep original execDocker (if present) so tests can restore it afterwards
    let fileModule = testpilot_subject.file_0013;
    let originalExecDocker;

    beforeEach(function() {
        originalExecDocker = fileModule.execDocker;
    });

    afterEach(function() {
        // Restore original execDocker (or delete if it was undefined)
        if (typeof originalExecDocker === 'undefined') {
            delete fileModule.execDocker;
        } else {
            fileModule.execDocker = originalExecDocker;
        }
    });

    it('returns exists:false and running:false when execDocker fails (non-zero code)', async function() {
        // Stub execDocker to simulate docker inspect command failing
        fileModule.execDocker = async function(args, opts) {
            // simulate a failure exit code
            return { code: 1, stdout: '' };
        };

        let res = await fileModule.dockerContainerState('nonexistent');
        assert.deepStrictEqual(res, { exists: false, running: false });
    });

    })