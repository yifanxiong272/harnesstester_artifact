let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0015.runtimeForLogger', function() {
        it('should call logger.info with joined args for log and writeStdout, and logger.error for error', function() {
            const calls = { info: [], error: [] };
            const fakeLogger = {
                info: function(...args) { calls.info.push(args); },
                error: function(...args) { calls.error.push(args); }
            };

            const exitFn = () => 'exited';
            const runtime = testpilot_subject.file_0015.runtimeForLogger(fakeLogger, exitFn);

            // log with multiple string args -> should be joined with single space and trimmed
            runtime.log('foo', 'bar');
            assert.strictEqual(calls.info.length, 1, 'logger.info should have been called once for log');
            assert.deepStrictEqual(calls.info[0], ['foo bar']);

            // error should call logger.error similarly
            runtime.error('bad', 'thing');
            assert.strictEqual(calls.error.length, 1, 'logger.error should have been called once for error');
            assert.deepStrictEqual(calls.error[0], ['bad thing']);

            // writeStdout should call logger.info with the raw value
            runtime.writeStdout('stdout-value');
            assert.strictEqual(calls.info.length, 2, 'logger.info should have been called again for writeStdout');
            assert.deepStrictEqual(calls.info[1], ['stdout-value']);
        });

            })
})