let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let fsp = fs.promises;
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: create a small directory tree for tests
    async function makeTree(root) {
        // root/
        //   a.txt
        //   dir1/
        //     b.txt
        //     subdir/
        //       c.txt
        //   dir2/
        //     d.txt
        await fsp.mkdir(root, { recursive: true });
        await fsp.writeFile(path.join(root, 'a.txt'), 'A');
        await fsp.mkdir(path.join(root, 'dir1', 'subdir'), { recursive: true });
        await fsp.writeFile(path.join(root, 'dir1', 'b.txt'), 'B');
        await fsp.writeFile(path.join(root, 'dir1', 'subdir', 'c.txt'), 'C');
        await fsp.mkdir(path.join(root, 'dir2'), { recursive: true });
        await fsp.writeFile(path.join(root, 'dir2', 'd.txt'), 'D');
    }

    // Helper: remove directory tree
    async function removeTree(root) {
        // Node 12+ has fs.rm with recursive; fall back to rmdir/rimraf style if needed
        if (fsp.rm) {
            await fsp.rm(root, { recursive: true, force: true });
        } else {
            // best-effort fallback
            const rimraf = async (p) => {
                try {
                    let stat = await fsp.lstat(p);
                    if (stat.isDirectory()) {
                        let entries = await fsp.readdir(p);
                        await Promise.all(entries.map(e => rimraf(path.join(p, e))));
                        await fsp.rmdir(p);
                    } else {
                        await fsp.unlink(p);
                    }
                } catch (e) {
                    // ignore
                }
            };
            await rimraf(root);
        }
    }

    // Helper to inspect call arguments for presence of a substring (filename)
    function callArgsContain(callArgs, substr) {
        for (let arg of callArgs) {
            if (typeof arg === 'string' && arg.includes(substr)) return true;
            if (arg && typeof arg.path === 'string' && arg.path.includes(substr)) return true;
            if (arg && typeof arg.name === 'string' && arg.name.includes(substr)) return true;
            // stats or other objects: check toString
            if (arg && typeof arg.toString === 'function') {
                try {
                    if (arg.toString().includes(substr)) return true;
                } catch (e) {}
            }
        }
        return false;
    }

    it('walk should visit at least all files in a small tree (matcher/visit are called)', async function() {
        // prepare temp directory
        const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fssearch-'));
        try {
            await makeTree(tmp);

            // instantiate service
            let svc = new testpilot_subject.file_0002.FsSearchService();

            // record calls
            let matcherCalls = [];
            let visitCalls = [];

            // matcher that always returns true but records args
            const matcher = function() {
                matcherCalls.push(Array.from(arguments));
                return true;
            };
            // Some implementations expect matcher to have an `ignores` method.
            // Provide a default no-op ignores() so the test doesn't fail.
            matcher.ignores = function() {
                // record ignore-check calls too (optional)
                matcherCalls.push(Array.from(arguments));
                // default: don't ignore anything
                return false;
            };

            // visit records its args (supporting async)
            const visit = async function() {
                visitCalls.push(Array.from(arguments));
            };

            // run walk. Use rootRel as empty string.
            await svc.walk(tmp, '', matcher, visit);

            // We expect matcher and visit to have been called at least several times
            assert(matcherCalls.length > 0, 'matcher was not called at all');
            assert(visitCalls.length > 0, 'visit was not called at all');

            // Ensure that each file we created appears in at least one visit call's arguments
            const expectedFiles = ['a.txt', path.join('dir1', 'b.txt'), path.join('dir1', 'subdir', 'c.txt'), path.join('dir2', 'd.txt')];
            for (let expected of expectedFiles) {
                let found = visitCalls.some(callArgs => callArgsContain(callArgs, expected));
                assert(found, `Expected visit to be called for ${expected}`);
            }
        } finally {
            await removeTree(tmp);
        }
    });

    })