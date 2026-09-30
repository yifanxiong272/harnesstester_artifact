let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case the async implementation is slow
    this.timeout(5000);

    let KimiCore;
    before(function() {
        // Make sure the expected class exists where documented
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0002, 'testpilot_subject.file_0002 should be present');
        KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(typeof KimiCore === 'function', 'KimiCore should be a constructor function');
    });

    describe('testpilot_subject.file_0002.KimiCore.prototype.setKimiConfig', function() {
        // Do not instantiate KimiCore here because its constructor may call rpcClient
        // which is not available in the test environment. We only need to verify
        // that setKimiConfig exists on the prototype.
        it('should be a function on the prototype', function() {
            assert.ok(typeof KimiCore.prototype.setKimiConfig === 'function',
                'setKimiConfig should exist on the prototype and be a function');
        });

    })
})