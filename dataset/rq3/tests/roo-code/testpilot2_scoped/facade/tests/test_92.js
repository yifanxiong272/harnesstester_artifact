let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0009.CodeIndexSearchService - is a constructor function and instantiates', function(done) {
        const Class = testpilot_subject.file_0009.CodeIndexSearchService;
        assert.equal(typeof Class, 'function', 'expected CodeIndexSearchService to be a function (constructor)');

        // provide simple, self-contained mock dependencies
        let configManager = { get: () => null };
        let stateManager = { set: () => null, get: () => null };
        let embedder = { embedText: () => [0, 0, 0] };
        let vectorStore = { add: () => null, query: () => [] };

        // Should construct without throwing
        let instance = new Class(configManager, stateManager, embedder, vectorStore);
        assert.ok(instance && typeof instance === 'object', 'expected constructor to return an object instance');

        done();
    });

    })