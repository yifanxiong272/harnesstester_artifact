let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const WorktreeService = testpilot_subject.file_0006 && testpilot_subject.file_0006.WorktreeService;
    const checkGitRepo = WorktreeService && WorktreeService.prototype && WorktreeService.prototype.checkGitRepo;

    it('exports WorktreeService.prototype.checkGitRepo', function() {
        assert.ok(WorktreeService, 'WorktreeService is present');
        assert.ok(checkGitRepo, 'checkGitRepo is present');
        assert.strictEqual(typeof checkGitRepo, 'function', 'checkGitRepo is a function');
    });

    })