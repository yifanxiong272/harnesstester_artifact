let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.WorkspaceAPI.prototype.onDidChangeConfiguration', function() {
        it('returns a disposable object with a dispose() function', function() {
            const apiProto = testpilot_subject.file_0009.WorkspaceAPI.prototype;
            const disposable = apiProto.onDidChangeConfiguration(function() {});
            assert.ok(disposable, 'expected a return value');
            assert.strictEqual(typeof disposable.dispose, 'function', 'dispose should be a function');

            // calling dispose should not throw; calling twice should also be safe
            disposable.dispose();
            disposable.dispose();
        });

            })
})