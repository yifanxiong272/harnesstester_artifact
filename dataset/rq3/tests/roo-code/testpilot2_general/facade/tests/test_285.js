let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WorktreeService.prototype.parseWorktreeOutput - empty output yields empty array', function(done) {
        let WorktreeService = testpilot_subject.file_0006.WorktreeService;
        // Try to construct an instance; if construction requires args, fall back to a plain prototype object.
        let service;
        try {
            service = new WorktreeService();
        } catch (e) {
            service = Object.create(WorktreeService.prototype);
        }

        // call the parser with an empty string
        let result = service.parseWorktreeOutput('', process.cwd());
        // Expect no entries for empty output
        assert.strictEqual(Array.isArray(result), true, 'result should be an array');
        assert.strictEqual(result.length, 0, 'empty output should produce empty array');
        done();
    });

    })