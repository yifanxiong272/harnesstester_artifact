let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0010.resolveExecDetail', function() {
        it('is deterministic for the same input (pure function behavior)', function() {
            const args = {
                exec: 'node',
                script: 'app.js',
                argv: ['--port', '3000'],
                env: { NODE_ENV: 'test' }
            };
            const r1 = testpilot_subject.file_0010.resolveExecDetail(args);
            const r2 = testpilot_subject.file_0010.resolveExecDetail(args);
            // same input should produce deeply equal outputs
            assert.deepStrictEqual(r1, r2);
        });

            })
})