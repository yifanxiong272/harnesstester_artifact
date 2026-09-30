let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0013.buildSandboxCreateArgs', function() {
    const build = testpilot_subject.file_0013.buildSandboxCreateArgs;

    function hasFlagPair(args, flag, value) {
        for (let i = 0; i < args.length - 1; i++) {
            if (args[i] === flag && args[i + 1] === value) return true;
        }
        return false;
    }

    it('builds basic create args and labels (name, sessionKey, createdAtMs, configHash, custom labels)', function() {
        const params = {
            name: "sb1",
            scopeKey: "scopeX",
            createdAtMs: 12345,
            configHash: "ch",
            labels: { "a": "b", "": "c", "x": "" },
            cfg: {
                tmpfs: [],
                capDrop: [],
                readOnlyRoot: false,
                dns: [],
                extraHosts: [],
                binds: [],
                env: {},
                pidsLimit: 0
            }
        };

        const args = build(params);

        // starts with create and name
        assert.strictEqual(args[0], "create");
        assert.strictEqual(args[1], "--name");
        assert.strictEqual(args[2], "sb1");

        // built-in labels
        assert(hasFlagPair(args, "--label", "openclaw.sandbox=1"));
        assert(hasFlagPair(args, "--label", "openclaw.sessionKey=scopeX"));
        assert(hasFlagPair(args, "--label", "openclaw.createdAtMs=12345"));

        // configHash label present
        assert(hasFlagPair(args, "--label", "openclaw.configHash=ch"));

        // custom label 'a=b' should be present, empty keys/values should be ignored
        assert(hasFlagPair(args, "--label", "a=b"));
        assert(!hasFlagPair(args, "--label", "=c"));
        assert(!hasFlagPair(args, "--label", "x="));

        // security-opt no-new-privileges always present
        assert(args.includes("--security-opt"));
        // ensure at least one occurrence of the no-new-privileges security option
        let foundNNP = false;
        for (let i = 0; i < args.length - 1; i++) {
            if (args[i] === "--security-opt" && args[i+1] === "no-new-privileges") {
                foundNNP = true;
                break;
            }
        }
        assert.strictEqual(foundNNP, true);
    });

    })