let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Use a slightly higher timeout in case of slow fs operations on CI
    this.timeout(5000);

    // Helper to create an instance without invoking unknown constructor logic:
    function makeFsServiceInstance() {
        const proto = testpilot_subject.file_0004.FsService.prototype;
        // Create an object with the correct prototype (avoids running constructor)
        const inst = Object.create(proto);
        // Provide a sessions Map-like object that has a get method
        inst.sessions = new Map();
        return inst;
    }

    it('statMany returns entries for existing files and null for missing ones', async function() {
        // prepare temp dir and files
        const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'statMany-test-'));
        try {
            const fileA = path.join(tmp, 'a.txt');
            const fileB = path.join(tmp, 'b.txt');
            fs.writeFileSync(fileA, 'hello A');
            // leave b.txt absent to test missing entry

            const svc = makeFsServiceInstance();
            const sessionId = 's1';
            svc.sessions.set(sessionId, { metadata: { cwd: tmp } });

            // call statMany with existing and non-existing path
            const req = { paths: ['a.txt', 'b.txt', './doesnotexist'] };
            const res = await svc.statMany(sessionId, req);

            // verify shape
            assert.ok(res && typeof res === 'object', 'result should be an object');
            assert.ok(res.entries && typeof res.entries === 'object', 'entries should be an object');

            // existing file should have non-null entry
            assert.ok(res.entries['a.txt'] !== null, 'existing file should produce a non-null entry');

            // missing files should be null
            assert.strictEqual(res.entries['b.txt'], null, 'missing file b.txt should produce null entry');
            assert.strictEqual(res.entries['./doesnotexist'], null, 'missing relative file should produce null entry');
        } finally {
            // cleanup
            try { fs.rmSync(tmp, { recursive: true, force: true }); } catch (e) {}
        }
    });

    })