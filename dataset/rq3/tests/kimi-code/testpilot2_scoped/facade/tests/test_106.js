let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.getExperimentalFeatures', function() {
        const KimiCore = testpilot_subject.file_0002.KimiCore;

        it('returns the value produced by experimentalFlags.explainAll()', function() {
            // Create an object that uses the KimiCore prototype but does not run its constructor.
            let instance = Object.create(KimiCore.prototype);

            // Make a simple experimentalFlags object whose explainAll returns a known value
            let flags = {
                called: false,
                thisValue: null,
                returnValue: { featureX: true, featureY: false },
                explainAll: function() {
                    this.called = true;
                    this.thisValue = this;
                    return this.returnValue;
                }
            };

            instance.experimentalFlags = flags;

            let result = instance.getExperimentalFeatures();

            // The result should be exactly the returned object
            assert.strictEqual(result, flags.returnValue);
            // explainAll should have been called once (we toggled a flag)
            assert.strictEqual(flags.called, true);
            // The 'this' inside explainAll should be the experimentalFlags object itself
            assert.strictEqual(flags.thisValue, flags);
        });

            })
})