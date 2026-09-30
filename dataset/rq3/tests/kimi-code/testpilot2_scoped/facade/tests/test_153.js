let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002.KimiCore;

    it('returns config when no input is provided (undefined)', async function() {
        // Create an instance without invoking unknown constructor logic
        const instance = Object.create(KimiCore.prototype);
        instance.config = { a: 1 };
        // Ensure reloadRuntimeConfig would fail if called erroneously
        instance.reloadRuntimeConfig = () => { throw new Error('reloadRuntimeConfig should not be called'); };

        const res = await instance.getKimiConfig();
        assert.strictEqual(res, instance.config);
        assert.deepStrictEqual(res, { a: 1 });
    });

    })