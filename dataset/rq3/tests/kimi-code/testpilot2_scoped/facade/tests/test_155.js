let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const method = testpilot_subject.file_0002.KimiCore.prototype.getConfigDiagnostics;

    it('returns the configWarnings value set on this as warnings', async function() {
        const warningsArr = ['warn1', 'warn2'];
        const fakeThis = { configWarnings: warningsArr };

        const res = await method.call(fakeThis, { some: 'input' });

        // should be an object with a single "warnings" property that is the same reference
        assert.deepStrictEqual(Object.keys(res), ['warnings']);
        assert.strictEqual(res.warnings, warningsArr);
        assert.deepStrictEqual(res.warnings, ['warn1', 'warn2']);
    });

    })