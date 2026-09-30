let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('OutputManager class and prototype method exist', function() {
        // Ensure the module and the path to the constructor exist
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should be present');
        assert.ok(typeof testpilot_subject.file_0002.OutputManager === 'function',
            'OutputManager should be a constructor function');

        // The prototype should contain the method
        const proto = testpilot_subject.file_0002.OutputManager.prototype;
        assert.ok(proto, 'OutputManager.prototype should exist');
        assert.strictEqual(typeof proto.outputCommandOutput, 'function',
            'outputCommandOutput should be a function on the prototype');

        // The function is expected to accept four parameters (ts, text, isPartial, alreadyDisplayedComplete)
        // This checks the declared arity, not runtime behavior.
        assert.strictEqual(proto.outputCommandOutput.length, 4,
            'outputCommandOutput should declare 4 parameters');
    });

    })