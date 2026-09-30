let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0009.WorkspaceAPI.prototype.registerTextDocumentContentProvider', function() {

    it('should return an object with a dispose function named "dispose"', function() {
        const result = testpilot_subject.file_0009.WorkspaceAPI.prototype.registerTextDocumentContentProvider('myscheme', () => {});
        assert.strictEqual(typeof result, 'object', 'result should be an object');
        assert.ok(result.hasOwnProperty('dispose'), 'result should have a dispose property');
        assert.strictEqual(typeof result.dispose, 'function', 'dispose should be a function');
        // Function should have the name "dispose"
        assert.strictEqual(result.dispose.name, 'dispose', 'dispose function should be named "dispose"');
    });

    })