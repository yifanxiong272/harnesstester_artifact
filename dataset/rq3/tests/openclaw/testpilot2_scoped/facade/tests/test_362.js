let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subject = testpilot_subject.file_0013;
    const fnName = 'readDockerContainerEnvVar';
    // Save original execDocker if present so we can restore it
    const origExec = subject.execDocker;

    afterEach(function() {
        // Restore original execDocker (or delete the stub) to avoid cross-test pollution
        if (origExec === undefined) {
            delete subject.execDocker;
        } else {
            subject.execDocker = origExec;
        }
    });

    it('returns null when execDocker fails (non-zero exit code)', async function() {
        subject.execDocker = async function(args, opts) {
            return { code: 2, stdout: 'SHOULD=NOTMATTER\n' };
        };
        const res = await subject[fnName]('anyContainer', 'SHOULD');
        assert.strictEqual(res, null);
    });

    })