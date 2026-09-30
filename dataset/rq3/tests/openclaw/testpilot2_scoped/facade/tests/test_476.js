let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0016.resolveAcpClientSpawnEnv', function() {
    it('adds OPENCLAW_SHELL="acp-client" and preserves existing keys', function() {
        const baseEnv = { A: '1', B: '2' };
        const env = testpilot_subject.file_0016.resolveAcpClientSpawnEnv(baseEnv, {});
        assert.strictEqual(env.OPENCLAW_SHELL, 'acp-client', 'OPENCLAW_SHELL should be set to acp-client');
        assert.strictEqual(env.A, '1', 'existing key A should be preserved');
        assert.strictEqual(env.B, '2', 'existing key B should be preserved');
    });

    })