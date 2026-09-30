let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to accept several possible reasonable return shapes from unknown implementation.
    function assertResultContainsText(result, expectedText) {
        // Accept undefined (method may perform side-effects only)
        if (typeof result === 'undefined') return;

        // Accept string (maybe the rendered text)
        if (typeof result === 'string') {
            assert.ok(result.indexOf(expectedText) !== -1, 'string result should contain expected text');
            return;
        }

        // Accept object with a text-like property
        if (result && typeof result === 'object') {
            // Common possible property names
            const candidates = ['text', 'message', 'content', 'html'];
            for (let name of candidates) {
                if (typeof result[name] === 'string' && result[name].indexOf(expectedText) !== -1) return;
            }
            // If object contains array of chunks, search inside
            if (Array.isArray(result.chunks)) {
                for (let c of result.chunks) {
                    if (typeof c === 'string' && c.indexOf(expectedText) !== -1) return;
                    if (c && typeof c === 'object') {
                        if (typeof c.text === 'string' && c.text.indexOf(expectedText) !== -1) return;
                    }
                }
            }
            // If no known shape matched, fail
            assert.fail('result object did not contain expected text in known fields');
            return;
        }

        // For any other type, just fail
        assert.fail('Unexpected result type: ' + typeof result);
    }

    it('basic: should accept a simple non-partial message without throwing and (optionally) return or expose the text', function() {
        // instantiate OutputManager in a defensive way
        const OM = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.OutputManager;
        assert.ok(OM, 'OutputManager constructor should exist on testpilot_subject.file_0002');

        // Try creating with no args or an empty config if constructor expects something
        let omInstance;
        try {
            omInstance = new OM();
        } catch (e) {
            // If constructor requires arguments, try with an empty object
            omInstance = new OM({});
        }
        assert.ok(omInstance, 'should have an instance');

        const ts = Date.now();
        const text = 'Hello unit test';
        // Should not throw
        let result;
        assert.doesNotThrow(() => {
            result = omInstance.outputTextMessage(ts, text, false, false, false);
        }, 'outputTextMessage should not throw for basic call');

        // If a result is returned, it should contain the text in a reasonable way.
        assertResultContainsText(result, text);
    });

    })