let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('has CacheStrategy with calculateSystemTokens on its prototype', function() {
        // Ensure the constructor/path exists
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');

        // Navigate to the constructor under test
        let CS = testpilot_subject.file_0010 && testpilot_subject.file_0010.CacheStrategy;
        assert.strictEqual(typeof CS, 'function', 'CacheStrategy should be a constructor function');

        // The method should exist on the prototype
        assert.strictEqual(typeof CS.prototype.calculateSystemTokens, 'function',
            'calculateSystemTokens should be a function on the prototype');
    });

    })