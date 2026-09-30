let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.refreshAccessToken', function() {
    // Keep original globals to restore after tests
    const originalFetch = global.fetch;
    const moduleUnderTest = testpilot_subject.file_0001;

    afterEach(function() {
        // Restore fetch after each test
        global.fetch = originalFetch;
    });

    it('falls back to original credentials when refresh_token/email/accountId missing in response', async function() {
        moduleUnderTest.OPENAI_CODEX_OAUTH_CONFIG = {
            clientId: 'client-2',
            tokenEndpoint: 'https://example2.token'
        };
        moduleUnderTest.tokenResponseSchema = { parse(data) { return data; } };
        // extractAccountId returns undefined to force fallback
        moduleUnderTest.extractAccountId = function() { return undefined; };

        global.fetch = async function() {
            return {
                ok: true,
                status: 200,
                statusText: 'OK',
                async json() {
                    // Note: missing refresh_token and email
                    return {
                        access_token: 'access-only',
                        id_token: 'some-id',
                        expires_in: 10 // short expiry for easy assertion
                    };
                }
            };
        };

        const credentials = {
            refresh_token: 'fallback-refresh',
            email: 'fallback@example.com',
            accountId: 'acct-fallback'
        };

        const result = await moduleUnderTest.refreshAccessToken(credentials);

        assert.strictEqual(result.access_token, 'access-only');
        // refresh_token should fallback to credentials.refresh_token
        assert.strictEqual(result.refresh_token, credentials.refresh_token);
        // email should fallback
        assert.strictEqual(result.email, credentials.email);
        // accountId should fallback
        assert.strictEqual(result.accountId, credentials.accountId);
    });

    })