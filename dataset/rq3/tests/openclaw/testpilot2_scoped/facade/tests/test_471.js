let mocha = require('mocha');
let assert = require('assert');

// We need to ensure that when testpilot_subject requires 'import_provider_env_vars'
// it gets a predictable, local stub. We'll temporarily monkey-patch Node's module loader
// so that any require('import_provider_env_vars') returns our stub.
// This must be done before requiring testpilot_subject.
const Module = require('module');
const originalLoad = Module._load;

// Stubbed provider env var names returned for tests
const STUB_PROVIDER_ENV_VARS = ['PROV_A', 'PROV_B'];

Module._load = function(request, parent, isMain) {
    if (request === 'import_provider_env_vars') {
        return {
            listKnownProviderAuthEnvVarNames: () => STUB_PROVIDER_ENV_VARS.slice()
        };
    }
    return originalLoad.apply(this, arguments);
};

let testpilot_subject;
try {
    // Require after we've installed the stub so the module picks it up.
    testpilot_subject = require('..');
} finally {
    // Restore the original loader to avoid affecting other tests or modules.
    Module._load = originalLoad;
}

describe('test testpilot_subject', function() {
    describe('file_0016.buildAcpClientStripKeys', function() {
        it('returns an empty Set when no activeSkillEnvKeys and stripProviderAuthEnvVars is false', function() {
            const params = { stripProviderAuthEnvVars: false };
            const result = testpilot_subject.file_0016.buildAcpClientStripKeys(params);
            assert.ok(result instanceof Set, 'result should be a Set');
            assert.strictEqual(result.size, 0);
        });

            })
})