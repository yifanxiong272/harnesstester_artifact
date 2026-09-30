let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0004.summarizeConversation', function() {
    // Helper: attempt several common option shapes so tests are resilient to the exact option name used.
    async function tryCall(optionVariants) {
        let lastError;
        for (const opts of optionVariants) {
            try {
                // The function is declared async; it should return a Promise.
                const res = await testpilot_subject.file_0004.summarizeConversation(opts);
                return res;
            } catch (err) {
                lastError = err;
                // try next variant
            }
        }
        // If all variants rejected, throw the last error so the test fails with useful info.
        throw lastError || new Error('summarizeConversation rejected for all option variants');
    }

    // Helper: extract a human-readable summary string from possible return shapes.
    function extractSummary(result) {
        if (result == null) return null;
        if (typeof result === 'string') return result;
        if (typeof result === 'object') {
            // common shapes: { summary: '...' } or {text: '...'} or {result: '...'}
            if (typeof result.summary === 'string') return result.summary;
            if (typeof result.text === 'string') return result.text;
            if (typeof result.result === 'string') return result.result;
            // If object contains a top-level string property, return first one
            for (const k of Object.keys(result)) {
                if (typeof result[k] === 'string') return result[k];
            }
            // Not a string-bearing object; return JSON form so tests can still inspect determinism
            return JSON.stringify(result);
        }
        // fallback for other types
        return String(result);
    }

    const sampleConversation = [
        { speaker: 'Alice', text: 'I have a question about my order.' },
        { speaker: 'Support', text: 'Sure, can you give me the order number?' },
        { speaker: 'Alice', text: 'It is 12345.' }
    ];

    it('returns a Promise when invoked', function() {
        // Call in one common shape; check it returns something with a .then function.
        const maybePromise = testpilot_subject.file_0004.summarizeConversation({ conversation: sampleConversation });
        assert.ok(maybePromise && typeof maybePromise.then === 'function', 'expected an object with then (a Promise)');
        // Return the promise so Mocha waits for it (ignore any rejection for this specific smoke test).
        return maybePromise.catch(() => {});
    });

    })