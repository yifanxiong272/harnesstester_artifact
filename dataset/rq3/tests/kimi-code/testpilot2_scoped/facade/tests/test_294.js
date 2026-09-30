let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.getPermission - exists', function() {
        // ensure the module and prototype chain exist and the method is a function
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should be present');
        assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore should be present');
        assert.ok(testpilot_subject.file_0002.KimiCore.prototype, 'KimiCore prototype should be present');
        assert.strictEqual(
            typeof testpilot_subject.file_0002.KimiCore.prototype.getPermission,
            'function',
            'getPermission should be a function on the prototype'
        );
    });

    })