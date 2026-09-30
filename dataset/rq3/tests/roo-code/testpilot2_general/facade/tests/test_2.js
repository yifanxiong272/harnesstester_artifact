let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to capture writes to stdout and stderr while running fn.
    function captureOutput(fn) {
        const stdoutWrite = process.stdout.write;
        const stderrWrite = process.stderr.write;
        let out = '', err = '';
        process.stdout.write = (chunk, encoding, cb) => {
            out += (typeof chunk === 'string') ? chunk : chunk.toString(encoding);
            if (typeof cb === 'function') cb();
            return true;
        };
        process.stderr.write = (chunk, encoding, cb) => {
            err += (typeof chunk === 'string') ? chunk : chunk.toString(encoding);
            if (typeof cb === 'function') cb();
            return true;
        };
        try {
            fn();
        } finally {
            process.stdout.write = stdoutWrite;
            process.stderr.write = stderrWrite;
        }
        return { out, err, combined: out + err };
    }

    it('OpenAiCodexOAuthManager.log should exist and be a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0001, 'file_0001 should be present');
        const Manager = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
        assert.ok(Manager, 'OpenAiCodexOAuthManager should be present');
        assert.strictEqual(typeof Manager.prototype.log, 'function', 'log should be a function on the prototype');
    });

    })