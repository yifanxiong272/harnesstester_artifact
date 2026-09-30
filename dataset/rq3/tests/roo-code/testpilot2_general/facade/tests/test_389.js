let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0009.WorkspaceAPI.prototype.findFiles - is defined', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0009, 'file_0009 namespace should be present');
        const proto = testpilot_subject.file_0009.WorkspaceAPI.prototype;
        assert.strictEqual(typeof proto.findFiles, 'function', 'findFiles should be a function on the prototype');
    });

    })