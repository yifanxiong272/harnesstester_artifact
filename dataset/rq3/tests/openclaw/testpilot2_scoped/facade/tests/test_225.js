let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const file0008 = testpilot_subject.file_0008;
    const detect = file0008 && file0008.detectCursorKeyMode;

    it('exports detectCursorKeyMode as a function', function() {
        assert.strictEqual(typeof detect, 'function');
    });

    // Helper to build a raw value that matches the type expected by detectCursorKeyMode.
    // If any of the provided parts or the module constants are Buffers, this returns a Buffer.
    function buildRaw(parts) {
        const hasBufferPart = parts.some(p => Buffer.isBuffer(p));
        if (hasBufferPart) {
            const bufs = parts.map(p => Buffer.isBuffer(p) ? p : Buffer.from(String(p)));
            return Buffer.concat(bufs);
        }
        return parts.join('');
    }

    })