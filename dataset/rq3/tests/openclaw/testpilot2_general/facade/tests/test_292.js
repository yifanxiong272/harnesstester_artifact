let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: create a version of sanitizeHostBaseEnv that uses our injected danger-check function.
    function makeSanitizerWithDangerFn(isDangerousFn) {
        const orig = testpilot_subject.file_0009.sanitizeHostBaseEnv;
        const src = orig.toString();
        // Replace the internal call to import_host_env_security.isDangerousHostEnvVarName with our stub.
        // Allow optional whitespace to match formatting differences.
        const modifiedSrc = src.replace(/\(0,\s*import_host_env_security\.isDangerousHostEnvVarName\)\(upperKey\)/g, '__isDangerous(upperKey)');
        // Build a new function that closes over our __isDangerous implementation.
        const maker = new Function('__isDangerous', 'return ' + modifiedSrc);
        return maker(isDangerousFn);
    }

    it('preserves PATH regardless of case of the key (keeps original key casing)', function() {
        // Stub that marks nothing as dangerous.
        const sanitize = makeSanitizerWithDangerFn(() => false);
        const env = {
            Path: '/usr/bin',       // mixed-case key should be treated as PATH and preserved under the same key name
            PATH: '/bin',           // if both present, both should be preserved independently (original function uses key as-is)
            other: 'value'
        };
        const out = sanitize(env);
        // Should keep both Path and PATH as provided, and also keep the non-dangerous 'other' key.
        assert.strictEqual(out.Path, '/usr/bin');
        assert.strictEqual(out.PATH, '/bin');
        assert.strictEqual(out.other, 'value');
    });

    })