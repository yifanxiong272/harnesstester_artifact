let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const build = testpilot_subject.file_0009.buildExecRuntimeErrorOutcome;

    it('should return an object when called with empty options (avoids reading properties of undefined)', function(done) {
        // call with an empty object so the implementation doesn't try to read properties from undefined
        let result = build({});

        assert.ok(result && typeof result === 'object', 'result must be a non-null object when called with empty options');
        assert.doesNotThrow(() => JSON.stringify(result), 'result should be serializable to JSON even when no params provided');

        done();
    });

})