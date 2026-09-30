let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout a little in case of slow fs on CI
    this.timeout(5000);

    const FsServiceStat = testpilot_subject.file_0004.FsService.prototype.stat;
    let tmpDir;

    // A minimal sessions object that matches what stat() expects:
    // sessions.get(sessionId) => { metadata: { cwd: tmpDir } }
    function makeThis() {
        return {
            sessions: {
                get: async (sessionId) => {
                    if (sessionId !== 'sess') throw new Error('unknown session');
                    return { metadata: { cwd: tmpDir } };
                }
            }
        };
    }

    before(function() {
        // create temporary directory and some entries inside
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fsServiceTest-'));
        // create a file
        fs.writeFileSync(path.join(tmpDir, 'file.txt'), 'hello world', 'utf8');
        // create a subdirectory
        fs.mkdirSync(path.join(tmpDir, 'subdir'));
    });

    after(function() {
        // cleanup recursively
        try {
            // Node >=12.10: fs.rmSync with recursive
            if (fs.rmSync) {
                fs.rmSync(tmpDir, { recursive: true, force: true });
            } else {
                // fallback
                const rimraf = (p) => {
                    if (!fs.existsSync(p)) return;
                    for (const entry of fs.readdirSync(p)) {
                        const full = path.join(p, entry);
                        const st = fs.lstatSync(full);
                        if (st.isDirectory()) rimraf(full);
                        else fs.unlinkSync(full);
                    }
                    fs.rmdirSync(p);
                };
                rimraf(tmpDir);
            }
        } catch (e) {
            // ignore cleanup errors in tests
        }
    });

    it('stat should resolve for cwd (path ".") and return a value', async function() {
        const thisArg = makeThis();
        const result = await FsServiceStat.call(thisArg, 'sess', { path: '.' });
        // We don't know exact shape of returned object from buildFsEntryFromStat,
        // but it should be truthy and should at least contain a string path or name.
        assert.ok(result, 'expected a result from stat');
    });

    })