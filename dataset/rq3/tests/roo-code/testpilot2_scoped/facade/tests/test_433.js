let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to normalize the return value from tiktoken into a predictable shape
    // Recognizes:
    // - a number (interpreted as token count)
    // - an array (interpreted as a token list)
    // - an object with a .tokens array
    // - an object with a numeric .length
    function canonicalize(result) {
        if (typeof result === 'number') {
            return { kind: 'count', count: result };
        }
        if (Array.isArray(result)) {
            return { kind: 'tokens', tokens: result.slice() };
        }
        if (result && typeof result === 'object') {
            if (Array.isArray(result.tokens)) {
                return { kind: 'tokens', tokens: result.tokens.slice() };
            }
            if (typeof result.length === 'number') {
                return { kind: 'count', count: result.length };
            }
        }
        // Fallback: try to treat as stringifiable array-like
        if (result && typeof result === 'object') {
            try {
                let json = JSON.stringify(result);
                // If it stringifies, consider that a stable representation for equality checks
                return { kind: 'opaque', json };
            } catch (e) {
                assert.fail('tiktoken returned an unsupported/unknown shape that tests cannot normalize');
            }
        }
        assert.fail('tiktoken returned an unsupported type: ' + typeof result);
    }

    it('returns zero tokens for empty string', async function() {
        let result = await testpilot_subject.file_0022.tiktoken('');
        let canon = canonicalize(result);
        if (canon.kind === 'count') {
            assert.strictEqual(canon.count, 0, 'expected token count 0 for empty string');
        } else if (canon.kind === 'tokens') {
            assert.strictEqual(canon.tokens.length, 0, 'expected zero-length token array for empty string');
        } else {
            // opaque: if it provides a JSON representation, assert it contains an empty indicator
            assert.ok(/0|""|\[\]/.test(canon.json), 'expected representation for empty input to indicate emptiness');
        }
    });

    })