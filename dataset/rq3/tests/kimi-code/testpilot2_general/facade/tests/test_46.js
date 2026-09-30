let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a temporary directory for each test
    async function makeTempDir() {
        const prefix = path.join(os.tmpdir(), 'testpilot-');
        return await fs.promises.mkdtemp(prefix);
    }

    it('test testpilot_subject.file_0002.FsSearchService.prototype.matcher - ignores .git/ by default', async function() {
        const dir = await makeTempDir();
        try {
            // Provide a minimal "this" for the prototype method (needs gitignoreCache map)
            const serviceLike = { gitignoreCache: new Map() };
            const ig = await testpilot_subject.file_0002.FsSearchService.prototype.matcher.call(serviceLike, dir);

            // The returned object should have an .ignores function (from the "ignore" package)
            assert.strictEqual(typeof ig.ignores, 'function');

            // .git/ should be ignored by default because matcher adds ".git/"
            assert.strictEqual(ig.ignores('.git/somefile'), true);
            assert.strictEqual(ig.ignores('.git/another/path'), true);
        } finally {
            // no files created, just remove directory
            await fs.promises.rmdir(dir);
        }
    });

    })