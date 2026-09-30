let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const originalFetch = global.fetch;

    beforeEach(function() {
        // ensure there's always a fetch to replace
        global.fetch = originalFetch || undefined;
    });

    afterEach(function() {
        // restore original fetch if it existed
        global.fetch = originalFetch;
    });

    it('exchangeCodeForTokens - success path returns tokens and computed expiry', async function() {
        // Arrange: prepare a successful token response
        const now = Date.now();
        const mockResponseData = {
            access_token: "atk-123",
            refresh_token: "rtk-456",
            expires_in: 3600, // 1 hour
            id_token: "id-789",
            email: "user@example.com"
        };

        let captured = { method: null, headers: null, body: null };

        global.fetch = async function(url, options) {
            captured.method = options && options.method;
            captured.headers = options && options.headers;
            captured.body = options && options.body;
            return {
                ok: true,
                status: 200,
                statusText: "OK",
                json: async () => JSON.parse(JSON.stringify(mockResponseData)), // return a copy
                text: async () => JSON.stringify(mockResponseData)
            };
        };

        // Act
        const res = await testpilot_subject.file_0001.exchangeCodeForTokens("the-code", "the-verifier");

        // Assert basic structure and values
        assert.strictEqual(res.type, "openai-codex");
        assert.strictEqual(res.access_token, mockResponseData.access_token);
        assert.strictEqual(res.refresh_token, mockResponseData.refresh_token);
        assert.strictEqual(res.email, mockResponseData.email);
        assert.ok(typeof res.expires === "number");
        // expires should be roughly now + 3600*1000 (allow some leeway)
        assert.ok(res.expires >= now + 3599 * 1000);
        assert.ok(res.expires <= now + 3605 * 1000);

        // Assert that fetch was called with POST and appropriate headers/body
        assert.strictEqual(captured.method, "POST");
        assert.ok(captured.headers && /application\/x-www-form-urlencoded/i.test(captured.headers["Content-Type"] || captured.headers["content-type"] || ""));
        assert.ok(typeof captured.body === "string");
        // body should contain the authorization code and code_verifier we passed
        assert.ok(captured.body.includes("code=the-code"));
        assert.ok(captured.body.includes("code_verifier=the-verifier"));
    });

    })