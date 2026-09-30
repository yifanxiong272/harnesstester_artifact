let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('path match trims and marks truncated when injected shorter than raw', function() {
        const fn = testpilot_subject.file_0017.buildBootstrapInjectionStats;
        const params = {
            injectedFiles: [
                // path has surrounding whitespace to test trimming
                { path: ' /some/dir/file1.txt ', content: 'HELLO' }
            ],
            bootstrapFiles: [
                // same path (with whitespace) and longer content -> truncated should be true
                { name: 'file1.txt', path: ' /some/dir/file1.txt ', content: 'HELLOWORLD', missing: false }
            ]
        };

        const res = fn(params);
        assert.strictEqual(res.length, 1, 'should return one stats object');

        const s = res[0];
        assert.strictEqual(s.name, 'file1.txt');
        // path should be trimmed
        assert.strictEqual(s.path, '/some/dir/file1.txt');
        assert.strictEqual(s.missing, false);
        assert.strictEqual(s.rawChars, 'HELLOWORLD'.trimEnd().length);
        assert.strictEqual(s.injectedChars, 'HELLO'.length);
        assert.strictEqual(s.truncated, true);
    });

    })