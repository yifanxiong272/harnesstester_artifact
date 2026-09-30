let mocha = require('mocha');
let assert = require('assert');

// We will stub child_process.exec and execSync so the tested function does not
// try to talk to a real Docker daemon. Stub is installed before requiring
// testpilot_subject so any child_process usage inside that module will use the stub.
const child_process = require('child_process');
const origExec = child_process.exec;
const origExecSync = child_process.execSync;

// Mapping of (container,label) to simulated docker output
const simulatedLabelOutputs = {
    // present -> return a normal value (with trailing newline as docker often does)
    'my-container|com.example.present': 'value-present\n',
    // empty value -> return empty string
    'my-container|com.example.empty': '\n',
    // missing label -> docker inspect templates often render "<no value>" for missing entries
    'my-container|com.example.missing': '<no value>\n',
    // complex value with quotes/newlines
    'my-container|com.example.complex': 'a "complex" value\n',
};

// For one test we simulate that docker (child_process) returns an error
const simulateErrorKey = 'my-container|com.example.error';

// Simple helper to extract label key from the command string. We do not try to be
// perfectly general; it's sufficient for the command shapes the real function
// is likely to use in tests below.
function extractLabelAndContainerFromCmd(cmd) {
    // cmd likely contains both the container name and the label; try to find known values
    // We'll look for the test container name and any of the test labels present in our map.
    const container = 'my-container';
    const testLabels = [
        'com.example.present',
        'com.example.empty',
        'com.example.missing',
        'com.example.complex',
        'com.example.error'
    ];
    for (let label of testLabels) {
        if (cmd.indexOf(label) !== -1 && cmd.indexOf(container) !== -1) {
            return { container, label };
        }
    }
    return null;
}

// Stub implementations
child_process.exec = function(cmd, opts, cb) {
    if (typeof opts === 'function') { cb = opts; opts = {}; }
    const pair = extractLabelAndContainerFromCmd(cmd);
    if (pair) {
        const key = `${pair.container}|${pair.label}`;
        if (key === simulateErrorKey) {
            // simulate async error from docker
            return process.nextTick(() => cb(new Error('simulated docker error'), '', 'error'));
        }
        const out = simulatedLabelOutputs[key] || '<no value>\n';
        return process.nextTick(() => cb(null, out, ''));
    }
    // fallback to original behavior if command not recognized
    return origExec.apply(this, arguments);
};

child_process.execSync = function(cmd, opts) {
    const pair = extractLabelAndContainerFromCmd(cmd);
    if (pair) {
        const key = `${pair.container}|${pair.label}`;
        if (key === simulateErrorKey) {
            // simulate a thrown error from execSync
            const err = new Error('simulated docker error');
            err.status = 1;
            throw err;
        }
        const out = simulatedLabelOutputs[key];
        // execSync typically returns a Buffer or string; returning a string is fine
        return out !== undefined ? out : '<no value>\n';
    }
    // fallback to original behavior
    return origExecSync.apply(this, arguments);
};

// Now require the module under test after stubbing child_process
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0013.readDockerContainerLabel (stubbed child_process)', function() {
    // restore child_process after all tests
    after(function() {
        child_process.exec = origExec;
        child_process.execSync = origExecSync;
    });

    it('returns null (or falsy) when the label is missing or rendered as "<no value>"', async function() {
        const value = await testpilot_subject.file_0013.readDockerContainerLabel('my-container', 'com.example.missing');
        // Accept either null, undefined, or empty string as "no label"
        assert.ok(value === null || value === undefined || value === '' , 'expected missing label to produce null/undefined/empty string');
    });

    })