let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let child_process = require('child_process');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // We'll create a temporary fake "docker" executable and prepend its directory to PATH
    // so that any call to the docker CLI by readDockerPort will hit our script.
    // On Windows we fall back to monkey-patching child_process.exec since making cmd shims is platform-specific.
    let tmpDir;
    let origPath;
    let origExec;

    beforeEach(function() {
        origPath = process.env.PATH;
        origExec = child_process.exec;
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'testpilot-docker-'));
    });

    afterEach(function() {
        // restore PATH and exec
        process.env.PATH = origPath;
        child_process.exec = origExec;

        // cleanup temp dir
        try {
            let files = fs.readdirSync(tmpDir);
            for (let f of files) {
                try { fs.unlinkSync(path.join(tmpDir, f)); } catch (e) {}
            }
            try { fs.rmdirSync(tmpDir); } catch (e) {}
        } catch (e) {}
    });

    function writeUnixDockerScript(content) {
        let scriptPath = path.join(tmpDir, 'docker');
        fs.writeFileSync(scriptPath, content, { mode: 0o755 });
        return scriptPath;
    }

    function writeWindowsDockerScript(content) {
        // create docker.cmd which will be found on Windows
        let scriptPath = path.join(tmpDir, 'docker.cmd');
        fs.writeFileSync(scriptPath, content, { mode: 0o755 });
        return scriptPath;
    }

    it('should extract a host port when docker prints a single mapping', async function() {
        // Prepare fake docker that prints a single mapping
        if (process.platform === 'win32') {
            // monkey-patch exec to simulate docker CLI output
            child_process.exec = function(cmd, opts, cb) {
                if (typeof opts === 'function') { cb = opts; opts = {}; }
                // simulate "docker port ...": output "0.0.0.0:32768\n"
                if (cb) cb(null, '0.0.0.0:32768\n', '');
                return { kill: function() {} };
            };
        } else {
            // write a small shell script that echoes the mapping
            let script = `#!/bin/sh
# simple docker shim that always prints a single mapping for port queries
echo "0.0.0.0:32768"
`;
            writeUnixDockerScript(script);
            // prepend our tmpDir to PATH
            process.env.PATH = tmpDir + path.delimiter + origPath;
        }

        // Call the function under test
        let result = await testpilot_subject.file_0013.readDockerPort('any-container', '80');
        // We don't assert on exact shape (string/number) since implementation may vary,
        // but ensure it contains the digits we provided.
        assert.ok(result !== undefined && result !== null, 'expected some result');
        assert.match(String(result), /32768/, 'result should include the host port 32768');
    });

    })