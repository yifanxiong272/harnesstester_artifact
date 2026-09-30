let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let fs = require('fs').promises;
let path = require('path');
let os = require('os');

describe('test testpilot_subject', function() {
    // Increase timeout in case filesystem is slow on CI
    this.timeout(5000);

    async function makeTempDir(prefix = 'tp-') {
        return await fs.mkdtemp(path.join(os.tmpdir(), prefix));
    }

    it('test testpilot_subject.file_0018.createRootScopedReadFile - reads a file inside the root', async function() {
        const rootDir = await makeTempDir('root-');
        const fileName = 'hello.txt';
        const content = 'hello world';
        const filePath = path.join(rootDir, fileName);

        try {
            await fs.writeFile(filePath, content, 'utf8');

            const createReader = testpilot_subject.file_0018.createRootScopedReadFile;
            const reader = createReader({ rootDir, rejectHardlinks: false, maxBytes: 1024 });

            // provide a relative path (common expected usage)
            const buffer = await reader(fileName);
            assert.strictEqual(Buffer.isBuffer(buffer), true, 'result should be a Buffer');
            assert.strictEqual(buffer.toString('utf8'), content);
        } finally {
            // Cleanup
            await fs.rm(rootDir, { recursive: true, force: true });
        }
    });

    })