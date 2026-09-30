let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const WorkspaceAPI = testpilot_subject.file_0009.WorkspaceAPI;
    // Ensure the class exists before running tests
    it('exports WorkspaceAPI constructor', function() {
        assert.ok(WorkspaceAPI, 'WorkspaceAPI should be exported');
        assert.equal(typeof WorkspaceAPI, 'function', 'WorkspaceAPI should be a function/class');
    });

    // temporary workspace directory for tests
    let tmpDir = null;

    before(function() {
        // create a temp directory for workspacePath that the tests can use
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wsapi-test-'));
    });

    after(function() {
        // cleanup the temporary directory created for tests (recursive remove to be safe)
        if (tmpDir && fs.existsSync(tmpDir)) {
            try {
                // Node 12+: rmdirSync with recursive; Node 14+ also has rmSync
                if (fs.rmSync) {
                    fs.rmSync(tmpDir, { recursive: true, force: true });
                } else {
                    fs.rmdirSync(tmpDir, { recursive: true });
                }
            } catch (e) {
                // best-effort cleanup; don't fail tests because of cleanup problem
            }
        }
    });

    })