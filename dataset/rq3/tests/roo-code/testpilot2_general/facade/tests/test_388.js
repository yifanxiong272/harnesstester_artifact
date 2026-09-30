let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.WorkspaceAPI.prototype.findFiles existence and shape', function() {
        it('WorkspaceAPI should be exported', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module should be present');
            assert.ok(testpilot_subject.file_0009, 'file_0009 namespace should be present');
            assert.ok(testpilot_subject.file_0009.WorkspaceAPI, 'WorkspaceAPI should be exported');
        });

            })
})