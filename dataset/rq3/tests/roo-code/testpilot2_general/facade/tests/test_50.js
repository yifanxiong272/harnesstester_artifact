let mocha = require('mocha');
let assert = require('assert');
let http = require('http');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // increase timeout because some tests involve real HTTP server interactions
    this.timeout(10 * 1000);

    const moduleUnderTest = testpilot_subject.file_0001;
    const Manager = moduleUnderTest.OpenAiCodexOAuthManager;
    const OPENAI_CODEX_OAUTH_CONFIG = moduleUnderTest.OPENAI_CODEX_OAUTH_CONFIG;
    const callbackPort = OPENAI_CODEX_OAUTH_CONFIG.callbackPort;

    // small helper to perform simple GET requests to the callback server
    function httpGet(path) {
        return new Promise((resolve, reject) => {
            http.get({ hostname: '127.0.0.1', port: callbackPort, path, agent: false }, (res) => {
                let body = '';
                res.setEncoding('utf8');
                res.on('data', (chunk) => body += chunk);
                res.on('end', () => resolve({ statusCode: res.statusCode, body }));
            }).on('error', reject);
        });
    }

    // Ensure each test starts with a fresh instance
    function makeManager() {
        return new Manager();
    }

    it('waitForCallback rejects if there is no pendingAuth', async function() {
        const mgr = makeManager();
        // ensure no pendingAuth
        mgr.pendingAuth = undefined;
        try {
            await mgr.waitForCallback();
            assert.fail('Expected waitForCallback to throw when there is no pending authorization flow');
        } catch (err) {
            assert.ok(err instanceof Error);
            assert.strictEqual(err.message, 'No pending authorization flow');
        }
    });

    })