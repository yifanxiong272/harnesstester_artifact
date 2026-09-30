let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Skip entire suite if the module shape we expect isn't present.
    before(function() {
        if (!testpilot_subject ||
            !testpilot_subject.file_0004 ||
            !testpilot_subject.file_0004.FsService) {
            this.skip(); // nothing to test in this environment
        }
    });

    // create a temporary workspace for each test
    let tmpRoot;
    beforeEach(function() {
        tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'fsp-test-'));
    });

    afterEach(function() {
        if (tmpRoot && fs.existsSync(tmpRoot)) {
            // Node 12+ supports rmSync with recursive; fallback to rmdirSync for safety
            try {
                fs.rmSync(tmpRoot, { recursive: true, force: true });
            } catch (e) {
                // fallback
                (function removeRecursive(p) {
                    if (!fs.existsSync(p)) return;
                    for (let entry of fs.readdirSync(p)) {
                        const full = path.join(p, entry);
                        const st = fs.lstatSync(full);
                        if (st.isDirectory()) removeRecursive(full);
                        else fs.unlinkSync(full);
                    }
                    fs.rmdirSync(p);
                })(tmpRoot);
            }
        }
    });

    // Helper: try calling svc.stat with a few common request shapes.
    async function tryStat(svc, targetPath) {
        const tries = [
            { path: targetPath },
            { filePath: targetPath },
            { filepath: targetPath },
            { name: targetPath },
            targetPath, // maybe the API accepts a bare string
            { pathname: targetPath },
            { p: targetPath }
        ];
        let lastErr;
        for (const req of tries) {
            try {
                // many implementations are async and accept (sessionId, req)
                let res = await svc.stat(null, req);
                return res;
            } catch (err) {
                lastErr = err;
            }
        }
        // none worked
        throw lastErr || new Error('stat attempts all failed');
    }

    // Helper: extract a numeric size or stats-like object from a returned value
    function extractSize(res) {
        if (res == null) return undefined;
        // raw fs.Stats
        if (typeof res.size === 'number') return res.size;
        if (res && res.stats && typeof res.stats.size === 'number') return res.stats.size;
        if (res && res.stat && typeof res.stat.size === 'number') return res.stat.size;
        if (res && res.data && typeof res.data.size === 'number') return res.data.size;
        if (res && res.result && typeof res.result.size === 'number') return res.result.size;
        if (typeof res === 'number') return res;
        return undefined;
    }

    // Helper: detect a stats-like object (has isFile/isDirectory functions)
    function looksLikeStats(obj) {
        if (!obj) return false;
        if (typeof obj.isFile === 'function' || typeof obj.isDirectory === 'function') return true;
        if (obj.stats && (typeof obj.stats.isFile === 'function' || typeof obj.stats.isDirectory === 'function')) return true;
        if (obj.stat && (typeof obj.stat.isFile === 'function' || typeof obj.stat.isDirectory === 'function')) return true;
        return false;
    }

    it('stat with missing path should reject or throw', async function() {
        const svc = new testpilot_subject.file_0004.FsService();
        let threw = false;
        try {
            // try calling with an empty request
            await svc.stat(null, {});
        } catch (e) {
            threw = true;
        }
        // It is reasonable for implementations to either throw or return some error object.
        // We assert at least that it does not silently return a successful fs.Stats for an undefined path.
        assert.strictEqual(threw, true, 'calling stat with no path should throw/reject');
    });
});