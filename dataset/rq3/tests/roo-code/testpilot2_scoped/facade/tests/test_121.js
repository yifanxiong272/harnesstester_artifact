let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const originalFetch = global.fetch;

    afterEach(function() {
        // restore global.fetch after each test to avoid side effects
        global.fetch = originalFetch;
    });

    it('returns base64 data URL when response contains b64_json', async function() {
        // stub fetch to return a successful response with b64_json
        global.fetch = async (url, options) => {
            return {
                ok: true,
                status: 200,
                statusText: 'OK',
                json: async () => ({ data: [{ b64_json: 'ABC123' }] }),
                text: async () => JSON.stringify({ data: [{ b64_json: 'ABC123' }] })
            };
        };

        const opts = {
            baseURL: 'https://api.test',
            authToken: 'token',
            model: 'gpt-image-1',
            prompt: 'make me an icon',
            outputFormat: 'png'
        };

        const result = await testpilot_subject.file_0011.generateImageWithImagesApi(opts);
        assert.strictEqual(result.success, true);
        assert.strictEqual(result.imageFormat, 'png');
        assert.strictEqual(result.imageData, 'data:image/png;base64,ABC123');
    });

    })