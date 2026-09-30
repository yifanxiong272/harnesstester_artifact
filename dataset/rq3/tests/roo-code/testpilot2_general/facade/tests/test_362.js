let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0009.WorkspaceAPI.prototype.onDidChangeConfiguration - exists and is a function', function() {
        assert.strictEqual(
            typeof testpilot_subject.file_0009.WorkspaceAPI.prototype.onDidChangeConfiguration,
            'function',
            'onDidChangeConfiguration should be a function on the prototype'
        );
    });

    })