let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const runtimeForLogger = testpilot_subject.file_0011.runtimeForLogger;

    it('writeStdout calls logger.info with the raw value', function() {
        const infoCalls = [];
        const logger = {
            info(msg) { infoCalls.push(msg); },
            error() { throw new Error('error should not be called in this test'); }
        };

        const runtime = runtimeForLogger(logger);
        runtime.writeStdout('plain string');
        runtime.writeStdout(12345);

        assert.strictEqual(infoCalls.length, 2);
        assert.strictEqual(infoCalls[0], 'plain string');
        assert.strictEqual(infoCalls[1], 12345);
    });

    })