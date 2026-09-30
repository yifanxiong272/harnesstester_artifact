let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subject = testpilot_subject.file_0011;
    const generate = subject.generateImageWithProvider;
    let originalFetch;

    // minimal helper to create a fake fetch Response-like object
    function makeResponse({ ok = true, status = 200, statusText = 'OK', textBody = '', jsonBody = null }) {
        return {
            ok,
            status,
            statusText,
            text: async () => (typeof textBody === 'function' ? textBody() : textBody),
            json: async () => {
                if (typeof jsonBody === 'function') return jsonBody();
                return jsonBody;
            }
        };
    }

    before(function() {
        originalFetch = global.fetch;
    });

    after(function() {
        global.fetch = originalFetch;
    });

    afterEach(function() {
        // ensure any test that replaced fetch doesn't leak
        global.fetch = originalFetch;
    });

    it('returns success with valid base64 png image', async function() {
        const base64 = 'data:image/png;base64,AAAABBBB';
        global.fetch = async () =>
            makeResponse({
                ok: true,
                jsonBody: {
                    choices: [
                        { message: { images: [{ image_url: { url: base64 } }] } }
                    ]
                }
            });

        const result = await generate({
            baseURL: 'https://example.com',
            authToken: 'tok',
            model: 'm',
            prompt: 'generate',
            inputImage: null
        });

        assert.strictEqual(result.success, true);
        assert.strictEqual(result.imageData, base64);
        assert.strictEqual(result.imageFormat, 'png');
    });

    })