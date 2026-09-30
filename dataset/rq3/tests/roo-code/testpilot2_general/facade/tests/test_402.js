let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic presence tests do not depend on any external resources.
    it('WorkspaceAPI and prototype.applyEdit should exist', function() {
        // Ensure the module exposes the expected path
        assert.ok(testpilot_subject, 'testpilot_subject module should be loadable');
        assert.ok(testpilot_subject.file_0009, 'file_0009 namespace should exist on module');
        const WorkspaceAPI = testpilot_subject.file_0009.WorkspaceAPI;
        assert.ok(WorkspaceAPI, 'WorkspaceAPI should be exported');
        assert.strictEqual(typeof WorkspaceAPI.prototype.applyEdit, 'function',
            'WorkspaceAPI.prototype.applyEdit should be a function');
    });

    })