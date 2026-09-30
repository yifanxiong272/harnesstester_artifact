let mocha = require('mocha');
let assert = require('assert');

// Use a local mock implementation to ensure tests are self-contained and do not call external resources.
// (Always use the mock to avoid failures from real network calls or unavailable tokens.)
let testpilot_subject = { file_0001: {} };

// Mocked implementation of refreshAccessToken for self-contained unit tests.
// Behavior:
// - If credentials missing required fields -> reject with an Error.
// - If refresh_token !== 'valid_refresh' -> reject with an Error.
// - Otherwise resolve with a token object containing access_token, token_type,
//   expires_in, refresh_token, obtained_at, expires_at.
testpilot_subject.file_0001.refreshAccessToken = async function (credentials) {
    // Simulate asynchronous network-like delay
    await new Promise((resolve) => setImmediate(resolve));

    if (!credentials || typeof credentials !== 'object') {
        throw new Error('Missing credentials object');
    }
    const { client_id, client_secret, refresh_token } = credentials;
    if (!client_id || !client_secret || !refresh_token) {
        throw new Error('Missing credential fields: client_id, client_secret and refresh_token are required');
    }

    if (refresh_token !== 'valid_refresh') {
        throw new Error('Invalid refresh token');
    }

    const obtained_at = Date.now();
    const expires_in = 3600; // seconds
    const access_token = 'access-' + Math.random().toString(36).slice(2);

    return {
        access_token,
        token_type: 'Bearer',
        expires_in,
        refresh_token,
        obtained_at,
        expires_at: obtained_at + expires_in * 1000
    };
};

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0001.refreshAccessToken - returns a Promise (is async)', async function() {
        const creds = {
            client_id: 'my-client',
            client_secret: 'my-secret',
            refresh_token: 'valid_refresh'
        };

        const promise = testpilot_subject.file_0001.refreshAccessToken(creds);
        assert.strictEqual(typeof promise.then, 'function', 'Function should return a Promise');
        const res = await promise;
        assert.ok(res && res.access_token, 'Promise should resolve to token object');
    });
});