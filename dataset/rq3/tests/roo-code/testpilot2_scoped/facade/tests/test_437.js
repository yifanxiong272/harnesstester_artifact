let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs').promises;
let path = require('path');
let os = require('os');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    this.timeout(5000);

    it('writes JSON file and can be read back', async function() {
        const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'testpilot-'));
        const filePath = path.join(tmpDir, 'data.json');
        const data = { a: 1, b: 'x', c: [1, 2, 3] };

        try {
            // should resolve without throwing
            await testpilot_subject.file_0024.safeWriteJson(filePath, data);

            // file should exist and contain the same data when parsed
            const content = await fs.readFile(filePath, 'utf8');
            const parsed = JSON.parse(content);
            assert.deepStrictEqual(parsed, data);
        } finally {
            // cleanup
            await fs.unlink(filePath).catch(() => {});
            await fs.rmdir(tmpDir).catch(() => {});
        }
    });

    })