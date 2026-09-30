let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // convenience reference to the module under test
    const mod = testpilot_subject.file_0013;
    let originalExecDocker;

    before(function() {
        // save original if present so we can restore later
        originalExecDocker = mod.execDocker;
    });

    after(function() {
        // restore original to avoid side effects for other tests
        if (originalExecDocker === undefined) {
            delete mod.execDocker;
        } else {
            mod.execDocker = originalExecDocker;
        }
    });

    it('returns null when execDocker fails (non-zero exit code)', async function() {
        // fake execDocker to simulate a failure
        mod.execDocker = async function(args, options) {
            // basic sanity checks about arguments forwarded by the function
            assert(Array.isArray(args), 'args should be an array');
            assert.strictEqual(options && options.allowFailure, true, 'allowFailure should be true');
            return { code: 1, stdout: 'something went wrong\n' };
        };

        const res = await mod.readDockerContainerLabel('containerX', 'some.label');
        assert.strictEqual(res, null);
    });

    })