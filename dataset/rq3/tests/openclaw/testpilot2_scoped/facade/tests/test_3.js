let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const classify = testpilot_subject.file_0001.classifyFailoverReason;

    it('classifies authentication-related messages as auth (consistent)', function() {
        let msg1 = 'Authentication failed: invalid API key';
        let msg2 = 'Auth error: 401 Unauthorized';
        let c1 = classify(msg1);
        let c2 = classify(msg2);

        // should return a string
        assert.strictEqual(typeof c1, 'string');
        assert.strictEqual(typeof c2, 'string');

        // both auth-like messages should map to the same category
        assert.strictEqual(c1, c2, `Expected same classification for auth messages, got "${c1}" and "${c2}"`);

        // and the category should indicate authentication (case-insensitive)
        assert.ok(c1.toLowerCase().includes('auth') || c1.toLowerCase().includes('authentication'),
            `Expected auth-like classification, got "${c1}"`);
    });

    })