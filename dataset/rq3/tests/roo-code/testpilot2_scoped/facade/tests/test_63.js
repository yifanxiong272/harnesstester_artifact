let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.OpenAICompatibleHandler.prototype.getLanguageModel', function() {
        it('returns the value produced by provider when called with config.modelId', function() {
            // create a plain object whose prototype is the handler prototype
            let proto = testpilot_subject.file_0008.OpenAICompatibleHandler.prototype;
            let handler = Object.create(proto);

            handler.config = { modelId: 'model-123' };
            handler.provider = function(id) {
                return 'value-for-' + id;
            };

            let result = handler.getLanguageModel();
            assert.strictEqual(result, 'value-for-model-123');
        });

            })
})