let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0013.resolveDockerSpawnInvocation - returns expected shape', function(done) {
        // basic invocation with empty args
        const result = testpilot_subject.file_0013.resolveDockerSpawnInvocation([]);
        // result should be an object with specific keys
        assert.strictEqual(typeof result, 'object', 'result should be an object');
        assert.ok('command' in result, 'result should have command');
        assert.ok('args' in result, 'result should have args');
        assert.ok('shell' in result, 'result should have shell (may be undefined or boolean)');
        assert.ok('windowsHide' in result, 'result should have windowsHide (may be undefined or boolean)');

        // types
        assert.strictEqual(typeof result.command, 'string', 'command should be a string');
        assert.ok(Array.isArray(result.args), 'args should be an array');

        done();
    });

    })