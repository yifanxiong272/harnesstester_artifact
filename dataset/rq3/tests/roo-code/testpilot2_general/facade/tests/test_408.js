let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.WorkspaceAPI.prototype.createFileSystemWatcher', function() {
        it('returns an object with onDidChange/onDidCreate/onDidDelete and dispose functions', function() {
            const workspaceProto = testpilot_subject.file_0009.WorkspaceAPI.prototype;
            assert.ok(typeof workspaceProto.createFileSystemWatcher === 'function');

            const watcher = workspaceProto.createFileSystemWatcher('**/*.js', false, false, false);
            assert.ok(watcher && typeof watcher === 'object', 'watcher should be an object');

            assert.strictEqual(typeof watcher.onDidChange, 'function', 'onDidChange should be a function');
            assert.strictEqual(typeof watcher.onDidCreate, 'function', 'onDidCreate should be a function');
            assert.strictEqual(typeof watcher.onDidDelete, 'function', 'onDidDelete should be a function');
            assert.strictEqual(typeof watcher.dispose, 'function', 'dispose should be a function');
        });

            })
})