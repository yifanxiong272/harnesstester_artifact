let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let fs = require('fs');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep originals so we can restore fs promises methods after each test
    let origPromises = fs.promises || {};
    let origRm = origPromises.rm;
    let origRmdir = origPromises.rmdir;

    afterEach(function() {
        // restore originals (handle the case where promises may be missing)
        if (!fs.promises) fs.promises = {};
        if (typeof origRm === 'undefined') {
            delete fs.promises.rm;
        } else {
            fs.promises.rm = origRm;
        }
        if (typeof origRmdir === 'undefined') {
            delete fs.promises.rmdir;
        } else {
            fs.promises.rmdir = origRmdir;
        }
    });

    it('does not attempt to delete when worktreePath equals cwd and should not perform removal', async function() {
        const cwd = '/same/path';
        const worktreePath = '/same/path';
        let called = false;

        if (!fs.promises) fs.promises = {};
        fs.promises.rm = async function(p, opts) {
            called = true;
            return;
        };
        fs.promises.rmdir = async function(p, opts) {
            called = true;
            return;
        };

        const svc = new testpilot_subject.file_0006.WorktreeService();

        // Act: deleting the current worktree should be a no-op (safety) and should not throw
        await svc.deleteWorktree(cwd, worktreePath, false);

        // Assert: no filesystem removal attempt when deleting the current worktree
        assert.strictEqual(called, false, 'expected no filesystem removal attempt when deleting the current worktree');
    });

    })