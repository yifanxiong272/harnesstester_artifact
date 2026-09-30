let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('normalizePath should be idempotent (normalizing twice yields same result) on various inputs', function(done) {
        let normalize = testpilot_subject.file_0006.WorktreeService.prototype.normalizePath;
        let cases = [
            'a/./b',
            './a/b',
            '../a/b',
            '/a//b///c',
            '/a/b/../c/..', // may normalize to '/a' or '/', but should be stable after one pass
            '/x/./y/../z//'
        ];
        for (let p of cases) {
            let n1 = normalize.call({}, p);
            let n2 = normalize.call({}, n1);
            assert.strictEqual(n2, n1, 'normalizePath should be idempotent for input: ' + p);
        }
        done();
    });

    })