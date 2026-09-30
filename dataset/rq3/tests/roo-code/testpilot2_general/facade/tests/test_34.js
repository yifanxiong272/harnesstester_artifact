let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype.getAccountId', function() {

        it('should exist and be a function', function() {
            let proto = testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype;
            assert.ok(proto, 'prototype not found');
            assert.strictEqual(typeof proto.getAccountId, 'function', 'getAccountId should be a function');
        });

            })
})