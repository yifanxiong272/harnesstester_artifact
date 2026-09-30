let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('FakeAIHandler and its getModel method should exist', function() {
        const modulePart = testpilot_subject && testpilot_subject.file_0016;
        assert.ok(modulePart, 'testpilot_subject.file_0016 is not present');
        const FakeAIHandler = modulePart.FakeAIHandler;
        assert.ok(FakeAIHandler, 'FakeAIHandler constructor not found');
        assert.strictEqual(typeof FakeAIHandler.prototype.getModel, 'function', 'getModel is not a function on the prototype');
    });

    })