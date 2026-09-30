let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WorktreeService.prototype.listWorktrees', function() {
        let mod = testpilot_subject.file_0006;
        let WorktreeService = mod.WorktreeService;
        let originalExecAsync;
        beforeEach(function() {
            // save original if present so we can restore it
            originalExecAsync = mod.execAsync;
        });
        afterEach(function() {
            // restore original to avoid affecting other tests
            if (typeof originalExecAsync !== 'undefined') {
                mod.execAsync = originalExecAsync;
            } else {
                delete mod.execAsync;
            }
        });

        it('returns empty array when execAsync throws/rejects', async function() {
            // Arrange: make execAsync throw
            mod.execAsync = async function() { throw new Error('simulated exec failure'); };

            const svc = new WorktreeService();

            // Make parseWorktreeOutput fail if called (it should not be called)
            let parseCalled = false;
            svc.parseWorktreeOutput = function() {
                parseCalled = true;
                return ['should-not-be-returned'];
            };

            // Act
            const result = await svc.listWorktrees('/irrelevant');

            // Assert
            assert.deepStrictEqual(result, [], 'listWorktrees returns empty array on exec failure');
            assert.strictEqual(parseCalled, false, 'parseWorktreeOutput should not be called when execAsync fails');
        });

            })
})