let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const moduleUnderTest = testpilot_subject.file_0006;
    const WorktreeService = moduleUnderTest.WorktreeService;

    let originalExecAsync;

    beforeEach(function() {
        // preserve any original execAsync so we can restore it
        originalExecAsync = moduleUnderTest.execAsync;
    });

    afterEach(function() {
        // restore original execAsync
        moduleUnderTest.execAsync = originalExecAsync;
    });

    it('returns null when git reports HEAD (detached)', async function() {
        const testCwd = "/another/fake/repo";

        moduleUnderTest.execAsync = async function(cmd, options) {
            // respond with HEAD to simulate detached HEAD
            return { stdout: "HEAD\n" };
        };

        const svc = new WorktreeService();
        const branch = await svc.getCurrentBranch(testCwd);
        assert.strictEqual(branch, null);
    });

    })