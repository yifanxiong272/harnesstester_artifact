let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const asRelativePath = testpilot_subject.file_0009.WorkspaceAPI.prototype.asRelativePath;

    it('returns the input fsPath when workspaceFolders is undefined', function() {
        const fsPath = path.join(path.sep, 'some', 'random', 'file.txt');
        const result = asRelativePath.call({}, fsPath, false);
        assert.strictEqual(result, fsPath);
    });

    })