let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.WorkspaceAPI.prototype.onDidChangeWorkspaceFolders', function() {
        it('should exist and be a function', function() {
            const WorkspaceAPI = testpilot_subject.file_0009.WorkspaceAPI;
            assert.ok(WorkspaceAPI, 'WorkspaceAPI constructor missing');
            // Provide a string path to avoid "The \"path\" argument must be of type string. Received undefined"
            const api = new WorkspaceAPI('/');
            assert.strictEqual(typeof api.onDidChangeWorkspaceFolders, 'function', 'onDidChangeWorkspaceFolders should be a function');
        });

            })
})