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

    it('walk should await asynchronous visit handlers (visit promises are awaited)', async function() {
        const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fssearch-'));
        try {
            await makeTree(tmp);

            let svc = new testpilot_subject.file_0002.FsSearchService();

            let visitOrder = [];
            // matcher should be callable but also provide an 'ignores' function that walk expects.
            const matcher = () => true;
            matcher.ignores = () => false;

            // visit simulates async work with small delay
            const visit = async function(...args) {
                const rel = args.find(a => typeof a === 'string' && a !== tmp) || args[0];
                // push before delay to mark start, then await and mark finish
                visitOrder.push({ when: 'start', arg: rel });
                await new Promise(resolve => setTimeout(resolve, 10));
                visitOrder.push({ when: 'end', arg: rel });
            };

            // Run walk and await completion. If walk does not await visit promises,
            // we might see visitOrder missing 'end' entries when walk resolves.
            await svc.walk(tmp, '', matcher, visit);

            // After walk completes, ensure that for every 'start' there is a corresponding 'end'.
            const starts = visitOrder.filter(e => e.when === 'start').length;
            const ends = visitOrder.filter(e => e.when === 'end').length;
            assert.strictEqual(starts, ends, 'visit start/end counts should match, implying walk awaited the async visit handlers');
            assert(starts > 0, 'visit should have been invoked at least once');
        } finally {
            await removeTree(tmp);
        }
    });
});