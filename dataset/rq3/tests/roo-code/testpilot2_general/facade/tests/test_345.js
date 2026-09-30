let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Utilities for tests
    function makeTempDir(prefix = 'ws-') {
        return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    }
    function makeTempFile(dir, name, content) {
        const p = path.join(dir, name);
        fs.writeFileSync(p, content, 'utf8');
        return p;
    }
    // A minimal Uri.file replacement for constructing edit maps / calling API.
    // The WorkspaceAPI implementation inside testpilot_subject will construct its own Uri for workspace folders,
    // but for calls from the tests we can pass objects that expose fsPath.
    const Uri = { file: (p) => ({ fsPath: p }) };

    describe('file_0009.WorkspaceAPI', function() {
        let workspaceDir;
        let otherDir;
        let api;

        beforeEach(function() {
            workspaceDir = makeTempDir('workspace-');
            otherDir = makeTempDir('workspace-other-');
            // Create the WorkspaceAPI instance. Provide a minimal context object.
            api = new testpilot_subject.file_0009.WorkspaceAPI(workspaceDir, {});
        });

        afterEach(function() {
            // cleanup created files and folders under the two dirs
            // remove files then directories
            function rmdirRecursive(p) {
                if (!fs.existsSync(p)) return;
                const stat = fs.statSync(p);
                if (stat.isDirectory()) {
                    for (const entry of fs.readdirSync(p)) {
                        rmdirRecursive(path.join(p, entry));
                    }
                    try { fs.rmdirSync(p); } catch (e) {}
                } else {
                    try { fs.unlinkSync(p); } catch (e) {}
                }
            }
            rmdirRecursive(workspaceDir);
            rmdirRecursive(otherDir);
        });

        it('asRelativePath returns full path for outside files and relative for inside files', function() {
            // file outside workspace
            const outsideFile = makeTempFile(os.tmpdir(), `outside-${Date.now()}.txt`, 'outside');
            const rOutside = api.asRelativePath(outsideFile, false);
            assert.strictEqual(rOutside, outsideFile, 'Outside file should return full fs path');

            // file inside workspace
            const insideFile = makeTempFile(workspaceDir, 'inside.txt', 'hello\nworld');
            const expectedRel = path.relative(workspaceDir, insideFile);
            const rInside = api.asRelativePath(insideFile, false);
            assert.strictEqual(rInside, expectedRel, 'Inside file should return relative path');
        });

            })
})