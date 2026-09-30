let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

const fs = require('fs');
const fsp = fs.promises;
const os = require('os');
const path = require('path');

describe('test testpilot_subject', function() {
    // Basic test: walk visits files and directories (no matcher)
    it('test testpilot_subject.file_0002.FsSearchService.prototype.walk - visits files and dirs', async function() {
        // create temporary directory structure
        const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fsp-test-'));
        try {
            // structure:
            // tmp/
            //   file1.txt
            //   dirA/
            //     file2.txt
            //     dirB/
            await fsp.writeFile(path.join(tmp, 'file1.txt'), 'hello');
            await fsp.mkdir(path.join(tmp, 'dirA'));
            await fsp.writeFile(path.join(tmp, 'dirA', 'file2.txt'), 'world');
            await fsp.mkdir(path.join(tmp, 'dirA', 'dirB'));

            const svc = new testpilot_subject.file_0002.FsSearchService();

            const visited = [];
            const visit = async (childRel, name, kind) => {
                visited.push({ childRel, name, kind });
            };

            // call walk with rootRel = "" so it starts at top of tmp
            await svc.walk(tmp, "", null, visit);

            // Convert to a set of key strings for easier assertions
            const seen = new Set(visited.map(e => `${e.childRel}|${e.kind}`));
            const expected = [
                'file1.txt|file',
                'dirA|directory',
                'dirA/file2.txt|file',
                'dirA/dirB|directory'
            ];
            for (const exp of expected) {
                assert.ok(seen.has(exp), `Expected visited to include ${exp}, saw: ${[...seen].join(', ')}`);
            }
            // also ensure nothing unexpected (at least these expected count)
            assert.ok(seen.size >= expected.length);
        } finally {
            // cleanup
            await fsp.rm(tmp, { recursive: true, force: true });
        }
    });

    // Test: walker respects matcher.ignores
    })