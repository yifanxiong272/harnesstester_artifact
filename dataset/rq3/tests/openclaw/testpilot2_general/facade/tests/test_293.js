let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0009.sanitizeHostBaseEnv', function() {
    it('does not throw for a variety of inputs', function() {
        const fn = testpilot_subject.file_0009.sanitizeHostBaseEnv;
        const inputs = [
            undefined,
            null,
            0,
            1,
            '',
            'string',
            true,
            false,
            [],
            {},
            { HOST: 'example.com', PORT: '80' },
            [{ foo: 'bar' }]
        ];

        inputs.forEach((inp) => {
            assert.doesNotThrow(() => {
                // call with an empty object when inp is null/undefined to avoid
                // "Cannot convert undefined or null to object" errors in the function
                if (inp == null) {
                    fn({});
                } else {
                    fn(inp);
                }
            }, `sanitizeHostBaseEnv threw for input: ${JSON.stringify(inp)}`);
        });
    });

});