let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject.file_0006.WorktreeService.prototype.createWorktree', function() {
    // create a temporary directory to use as a cwd for tests
    let tmpDir;
    let svc;

    before(function() {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wt-test-'));
        // instantiate the service under test
        let W = testpilot_subject && testpilot_subject.file_0006 && testpilot_subject.file_0006.WorktreeService;
        assert.ok(typeof W === 'function', 'WorktreeService constructor should exist');
        svc = new W();
        assert.ok(svc, 'WorktreeService instance created');
    });

    after(function() {
        // cleanup the temporary directory (be tolerant if something created files inside)
        try {
            fs.rmSync(tmpDir, { recursive: true, force: true });
        } catch (e) {
            // ignore cleanup errors
        }
    });

    it('should expose createWorktree as an async function / thenable-returning method', function() {
        assert.ok(typeof svc.createWorktree === 'function', 'createWorktree should be a function');
        // If it was defined with async keyword, constructor name is "AsyncFunction"
        if (svc.createWorktree.constructor && svc.createWorktree.constructor.name) {
            assert.ok(
                svc.createWorktree.constructor.name === 'AsyncFunction' ||
                svc.createWorktree.constructor.name === 'Function',
                'createWorktree should be an async function (or at least a function)'
            );
        }
    });

    })