let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subjectPath = 'file_0002';
    const className = 'KimiCore';
    const methodName = 'setPermission';

    // Helper to obtain the function under test and fail with a helpful message if not found.
    function getSetPermissionFn() {
        assert.ok(
            testpilot_subject && typeof testpilot_subject === 'object',
            'testpilot_subject must be an object'
        );
        assert.ok(
            testpilot_subject[subjectPath],
            `expected testpilot_subject.${subjectPath} to exist`
        );
        const fileObj = testpilot_subject[subjectPath];
        assert.ok(
            fileObj[className],
            `expected ${subjectPath}.${className} to exist`
        );
        const KimiCore = fileObj[className];
        assert.ok(
            KimiCore.prototype && KimiCore.prototype[methodName],
            `expected ${className}.prototype.${methodName} to exist`
        );
        const fn = KimiCore.prototype[methodName];
        assert.strictEqual(
            typeof fn,
            'function',
            `${methodName} should be a function`
        );
        return fn;
    }

    it('exports the setPermission function at the expected path', function() {
        const fn = getSetPermissionFn();
        // Basic sanity: function name or toString should be available
        assert.ok(fn.toString().length > 0, 'function source should be retrievable');
    });

    })