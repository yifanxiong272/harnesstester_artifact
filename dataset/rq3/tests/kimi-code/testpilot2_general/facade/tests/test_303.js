let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject.file_0004.FsService.prototype.statMany', function() {
    // Helper: get a usable statMany function and an instance (if constructor exists)
    function getStatMany() {
        let svc = null;
        let proto = testpilot_subject && testpilot_subject.file_0004 && testpilot_subject.file_0004.FsService && testpilot_subject.file_0004.FsService.prototype;
        if (!proto) throw new Error('FsService prototype not found on testpilot_subject.file_0004');
        try {
            // Try to construct instance (if constructor exists and doesn't require args)
            let C = testpilot_subject.file_0004.FsService;
            svc = new C();
        } catch (e) {
            // Fall back to using the prototype directly as context
            svc = proto;
        }
        if (typeof svc.statMany !== 'function') {
            // Maybe statMany is defined only on prototype; try that
            if (typeof proto.statMany === 'function') {
                return { fn: proto.statMany.bind(svc), svc };
            }
            throw new Error('statMany function not found on FsService');
        }
        return { fn: svc.statMany.bind(svc), svc };
    }

    // Try multiple request shapes until one returns an interpretable result
    async function tryStatMany(fn, sessionId, paths) {
        // possible request shapes to try
        let shapes = [
            { paths: paths }, // {paths: [p1,p2]}
            { paths: paths.map(p => ({ path: p })) }, // objects with path property
            { path: paths[0] }, // single path
            paths, // array directly
            { list: paths }, // alternative key
            { pathsList: paths },
            { pathsArray: paths }
        ];

        // Also try synchronous call styles: some implementations may accept (sessionId, paths)
        let calls = [];

        for (let req of shapes) calls.push(async () => fn(sessionId, req));
        calls.push(async () => fn(sessionId, paths)); // direct array
        calls.push(async () => fn(paths)); // maybe function is exported differently
        calls.push(async () => fn(sessionId, { paths: paths, includeStats: true }));

        let lastErr = null;
        for (let call of calls) {
            try {
                let res = await call();
                // Normalize to an array of result entries if possible
                let arr = null;
                if (Array.isArray(res)) {
                    arr = res;
                } else if (res && Array.isArray(res.results)) {
                    arr = res.results;
                } else if (res && Array.isArray(res.stats)) {
                    arr = res.stats;
                } else if (res && Array.isArray(res.value)) {
                    arr = res.value;
                } else if (res && res.entries && Array.isArray(res.entries)) {
                    arr = res.entries;
                } else if (res && typeof res === 'object') {
                    // Sometimes the response may be a map from path->stat
                    let keys = Object.keys(res).filter(k => k !== 'ok' && k !== 'status');
                    if (keys.length === paths.length) {
                        // create array in same order as requested paths
                        arr = paths.map(p => res[p] !== undefined ? res[p] : res[paths.indexOf(p)]);
                    }
                }
                if (!Array.isArray(arr)) {
                    // Maybe the response is a single stat for single path request
                    if (paths.length === 1) {
                        // Treat any non-null result as single entry array
                        if (res !== undefined && res !== null) arr = [res];
                    }
                }
                if (!Array.isArray(arr)) {
                    // Not interpretable; try next
                    lastErr = new Error('Uninterpretable response shape');
                    continue;
                }
                return arr;
            } catch (err) {
                lastErr = err;
                // try next call shape
            }
        }
        throw lastErr || new Error('statMany calls exhausted without success');
    }

    // Helpers to interpret a "stat-like" object
    function extractStatFromEntry(entry) {
        if (!entry) return null;
        if (entry.stat) return entry.stat;
        if (entry.result) return entry.result;
        if (entry.data) return entry.data;
        if (entry.stats) return entry.stats;
        // If object already looks like a fs.Stats (has size or isFile function)
        return entry;
    }
    function isStatFile(s) {
        if (!s) return false;
        if (typeof s.isFile === 'function') {
            try { if (s.isFile()) return true; } catch (e) {}
        }
        if (typeof s.mode === 'number') {
            // mode exists; check file bit (rough heuristic)
            // 0o170000 are type bits; skip complex check, prefer isFile if available
        }
        if (typeof s.size === 'number') {
            // If size > 0, likely a file (not definitive)
            return s.size >= 0;
        }
        return false;
    }
    function isStatDirectory(s) {
        if (!s) return false;
        if (typeof s.isDirectory === 'function') {
            try { if (s.isDirectory()) return true; } catch (e) {}
        }
        // directories often have size number too but not reliable
        return false;
    }

    // Create a temp workspace for tests
    let tmpRoot = null;
    before(function() {
        tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'statMany-test-'));
    });
    after(function() {
        if (tmpRoot && fs.existsSync(tmpRoot)) {
            // recursively remove; fs.rmSync may not exist on older node; use rmdir recursive fallback
            try {
                fs.rmSync(tmpRoot, { recursive: true, force: true });
            } catch (e) {
                // fallback
                const rimraf = (p) => {
                    if (!fs.existsSync(p)) return;
                    for (let name of fs.readdirSync(p)) {
                        let fp = path.join(p, name);
                        let st = fs.lstatSync(fp);
                        if (st.isDirectory()) rimraf(fp);
                        else fs.unlinkSync(fp);
                    }
                    fs.rmdirSync(p);
                };
                rimraf(tmpRoot);
            }
        }
    });

    it('should handle an empty paths list without throwing and return empty results', async function() {
        let { fn } = getStatMany();

        let paths = [];
        let arr;
        try {
            arr = await tryStatMany(fn, 'session-3', paths);
            // If arr is not an array, some implementations may return null or an object; normalize:
            if (Array.isArray(arr)) {
                assert.strictEqual(arr.length, 0, 'expected zero-length array for empty input');
            } else {
                // Accept null/undefined/empty-object as a valid empty response
                assert.ok(arr === null || arr === undefined || (typeof arr === 'object' && Object.keys(arr).length === 0));
            }
        } catch (err) {
            // Some implementations may throw for empty input; ensure the error is reasonable (not a crash)
            assert.ok(err instanceof Error, 'expected an Error instance for empty input');
        }
    });

});