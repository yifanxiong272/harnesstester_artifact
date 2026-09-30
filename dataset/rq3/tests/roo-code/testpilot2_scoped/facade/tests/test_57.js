let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('formatWithoutCachePoints -> when no systemPrompt, passes empty systemBlocks to formatResult and uses messagesToContentBlocks result', function() {
        const proto = testpilot_subject.file_0006.MultiPointStrategy.prototype;
        // create a plain instance whose prototype is the real prototype
        const instance = Object.create(proto);

        // prepare config with no systemPrompt
        instance.config = {
            messages: [{role: 'user', content: 'hello'}]
        };

        // stub messagesToContentBlocks to verify it's called and return sentinel
        let receivedMessages = null;
        instance.messagesToContentBlocks = function(messages) {
            receivedMessages = messages;
            return [{type: 'msg', content: 'converted'}];
        };

        // stub formatResult to verify arguments and return a result
        let receivedSystemBlocks = null;
        let receivedMessageBlocks = null;
        instance.formatResult = function(systemBlocks, messageBlocks) {
            receivedSystemBlocks = systemBlocks;
            receivedMessageBlocks = messageBlocks;
            return {systemBlocks, messageBlocks, combined: 'ok'};
        };

        // call method
        const result = instance.formatWithoutCachePoints();

        // assertions
        assert.deepStrictEqual(receivedMessages, instance.config.messages, 'messagesToContentBlocks should be called with config.messages');
        assert.deepStrictEqual(receivedSystemBlocks, [], 'systemBlocks should be empty when config.systemPrompt is not set');
        assert.deepStrictEqual(receivedMessageBlocks, [{type: 'msg', content: 'converted'}], 'formatResult should receive the converted message blocks');
        assert.deepStrictEqual(result, {systemBlocks: [], messageBlocks: [{type: 'msg', content: 'converted'}], combined: 'ok'}, 'formatWithoutCachePoints should return the value returned by formatResult');
    });

    })