let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.getTools signature and basic behavior', function() {
        const KimiCoreModule = testpilot_subject && testpilot_subject.file_0002;
        const getTools = KimiCoreModule && KimiCoreModule.KimiCore && KimiCoreModule.KimiCore.prototype && KimiCoreModule.KimiCore.prototype.getTools;

        it('getTools should exist and be a function', function() {
            assert.ok(getTools, 'getTools is not exported/found on prototype');
            assert.strictEqual(typeof getTools, 'function', 'getTools should be a function');
        });

            })
})