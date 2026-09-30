let mocha = require('mocha');
let assert = require('assert');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject.file_0015.resolveCompletionCachePath', function() {
    const resolve = testpilot_subject.file_0015.resolveCompletionCachePath;

    function containsName(resultPath, name) {
        // Accept either the full name or the basename appearing in the path (case-sensitive)
        return resultPath.indexOf(name) !== -1 || resultPath.indexOf(path.basename(name)) !== -1;
    }

    it('returns a non-empty absolute string path for typical inputs', function() {
        let result = resolve('bash', 'mycli');
        assert.strictEqual(typeof result, 'string', 'result must be a string');
        assert.ok(result.length > 0, 'result must not be empty');
        assert.ok(path.isAbsolute(result), 'result should be an absolute path');
        assert.ok(containsName(result, 'mycli'), 'result should contain the binary name or its basename');
    });

    })