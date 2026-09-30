let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');
let crypto = require('crypto');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Small helper to try to extract string content from a variety of possible return shapes
    function extractStringContent(result) {
        if (result === null || result === undefined) return null;
        // Buffer
        if (Buffer.isBuffer(result)) return result.toString();
        if (typeof result === 'string') return result;
        if (typeof result === 'object') {
            // common container keys
            const keys = ['content', 'data', 'body', 'text', 'result'];
            for (let k of keys) {
                if (result.hasOwnProperty(k)) {
                    let v = result[k];
                    if (v === null || v === undefined) return null;
                    if (Buffer.isBuffer(v)) return v.toString();
                    if (typeof v === 'string') return v;
                }
            }
        }
        return null;
    }

    // Utility to create a temp file with given contents. Returns full path.
    async function makeTempFile(contents, ext = '.txt') {
        const name = 'tp_test_' + crypto.randomBytes(8).toString('hex') + ext;
        const dir = path.join(os.tmpdir(), 'tp_test_dir_' + crypto.randomBytes(6).toString('hex'));
        await fs.promises.mkdir(dir, { recursive: true });
        const full = path.join(dir, name);
        await fs.promises.writeFile(full, contents, 'utf8');
        return { dir, full };
    }

    it('readLocalFileSafely is a function and is async (returns a Promise)', function() {
        assert.strictEqual(typeof testpilot_subject.file_0018.readLocalFileSafely, 'function');
        // calling an async function returns a Promise; do not await here
        const maybePromise = testpilot_subject.file_0018.readLocalFileSafely();
        assert.ok(maybePromise && typeof maybePromise.then === 'function', 'expected an object with then (a Promise)');
    });

    })