let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports WorkspaceAPI with getConfiguration on its prototype', function() {
        assert.ok(testpilot_subject, 'module should be present');
        // ensure the nested path exists
        assert.ok(testpilot_subject.file_0009, 'file_0009 namespace should exist');
        assert.ok(testpilot_subject.file_0009.WorkspaceAPI, 'WorkspaceAPI should exist');
        const gp = testpilot_subject.file_0009.WorkspaceAPI.prototype.getConfiguration;
        assert.strictEqual(typeof gp, 'function', 'getConfiguration should be a function');
    });

    })