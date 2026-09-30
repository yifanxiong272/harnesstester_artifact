let mocha = require('mocha');
let assert = require('assert');
let vm = require('vm');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('does nothing when dockerImageExists returns true', async function() {
        // Get source of the real function and run it in a sandbox where dependencies are stubbed.
        const fnSrc = testpilot_subject.file_0013.ensureDockerImage.toString();

        const calls = [];
        const sandbox = {
            // stub: image exists
            dockerImageExists: async (image) => true,
            // stub: record calls
            execDocker: async (args) => { calls.push(args); },
            // stub import_constants
            import_constants: { DEFAULT_SANDBOX_IMAGE: 'default-image' }
        };

        const ensureDockerImage = vm.runInNewContext('(' + fnSrc + ')', sandbox);

        // Call with any image; since dockerImageExists returns true, execDocker should not be called.
        await ensureDockerImage('some-image');
        assert.strictEqual(calls.length, 0, 'execDocker should not be called when image exists');
    });

    })