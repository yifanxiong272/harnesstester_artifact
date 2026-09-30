let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0016.FakeAIHandler', function() {
    const FakeAIHandler = testpilot_subject.file_0016.FakeAIHandler;

    it('should cache fakeAi instances by id and allow removal from cache via removeFromCache', function() {
        const id = 'cache-test-id';

        const fakeAiA = {
            id,
            createMessage: async function* () { yield 'A'; },
            getModel: () => 'modelA',
            countTokens: () => 1,
            completePrompt: (p) => `A:${p}`
        };

        const fakeAiB = {
            id,
            createMessage: async function* () { yield 'B'; },
            getModel: () => 'modelB',
            countTokens: () => 2,
            completePrompt: (p) => `B:${p}`
        };

        // First handler caches fakeAiA
        const handler1 = new FakeAIHandler({ fakeAi: fakeAiA });
        // Second handler with a different object but same id should get the cached one (fakeAiA)
        const handler2 = new FakeAIHandler({ fakeAi: fakeAiB });

        assert.strictEqual(handler1.ai, handler2.ai, 'Handlers with same id should share cached ai object');
        // The cached object should be the original fakeAiA object (not fakeAiB)
        assert.strictEqual(handler1.ai, fakeAiA, 'Cached object should be the first object provided for that id');

        // removeFromCache should exist and remove the cached entry
        assert.strictEqual(typeof handler1.ai.removeFromCache, 'function', 'removeFromCache should be added to cached ai');
        handler1.ai.removeFromCache();

        const fakeAiC = {
            id,
            createMessage: async function* () { yield 'C'; },
            getModel: () => 'modelC',
            countTokens: () => 3,
            completePrompt: (p) => `C:${p}`
        };

        // Now that the cache was cleared, a new handler with same id should use fakeAiC
        const handler3 = new FakeAIHandler({ fakeAi: fakeAiC });
        assert.strictEqual(handler3.ai, fakeAiC, 'After removal, new fakeAi should be cached and used');
        assert.notStrictEqual(handler3.ai, handler1.ai, 'New cached ai should not equal previously cached ai');
    });

    })