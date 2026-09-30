let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0008.OpenAICompatibleHandler', function() {
    const OpenAICompatibleHandler = testpilot_subject.file_0008.OpenAICompatibleHandler;

    it('getLanguageModel uses the provider function with modelId', function() {
        // create an instance without running the constructor to avoid external calls
        const inst = Object.create(OpenAICompatibleHandler.prototype);
        inst.options = { some: 'opt' };
        inst.config = { modelId: 'gpt-test' };
        // stub provider
        inst.provider = function(modelId) {
            return { calledWith: modelId, value: 'MODEL-' + modelId };
        };

        const lm = inst.getLanguageModel();
        assert.deepStrictEqual(lm, { calledWith: 'gpt-test', value: 'MODEL-gpt-test' });
    });

    })