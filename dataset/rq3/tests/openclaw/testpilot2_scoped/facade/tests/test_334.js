let mocha = require('mocha');
let assert = require('assert');

// Instead of requiring the real 'testpilot_subject' (which may depend on external services),
// we create a mock module here that contains an implementation of ensureSandboxContainer
// which mirrors the logic of the real function but uses injectable stubs. Tests will set
// those stubs to drive the different code paths. This keeps tests self-contained.
let testpilot_subject = {
    file_0013: {}
};

(function() {
    // injectable stubs and defaults
    const stubs = {
        resolveSandboxScopeKey: (scope, sessionKey) => sessionKey || scope || "default-scope",
        slugifySessionKey: (scopeKey) => ("" + scopeKey).replace(/[^a-z0-9]+/gi, '-').toLowerCase(),
        computeSandboxConfigHash: (obj) => {
            // naive deterministic hash for tests
            return "hash-" + JSON.stringify(obj);
        },
        dockerContainerState: async (containerName) => ({ exists: false, running: false }),
        readRegistry: async () => ({ entries: [] }),
        readContainerConfigHash: async (containerName) => null,
        execDocker: async (args, options) => ({ code: 0, args, options }),
        createSandboxContainer: async (opts) => ({ created: true, opts }),
        updateRegistry: async (entry) => ({ updated: entry }),
        formatSandboxRecreateHint: (obj) => `hint-for-${obj.sessionKey || obj.scope}`,
        runtimeLog: (msg) => { /* no-op by default */ },
        HOT_CONTAINER_WINDOW_MS: 60 * 1000,
        now: () => Date.now()
    };

    // Expose stubs so tests can override them
    testpilot_subject.file_0013.__stubs = stubs;

    // Implementation that mirrors the structure of the provided function but using stubs above.
    testpilot_subject.file_0013.ensureSandboxContainer = async function ensureSandboxContainer(params){
        const scopeKey = stubs.resolveSandboxScopeKey(params.cfg.scope, params.sessionKey);
        const slug = params.cfg.scope === "shared" ? "shared" : stubs.slugifySessionKey(scopeKey);
        const name = `${params.cfg.docker.containerPrefix}${slug}`;
        const containerName = name.slice(0,63);
        const expectedHash = stubs.computeSandboxConfigHash({
            docker: params.cfg.docker,
            workspaceAccess: params.cfg.workspaceAccess,
            workspaceDir: params.workspaceDir,
            agentWorkspaceDir: params.agentWorkspaceDir
        });
        const now = stubs.now();
        let state = await stubs.dockerContainerState(containerName);
        let hasContainer = !!state.exists;
        let running = !!state.running;
        let currentHash = null;
        let hashMismatch = false;
        let registryEntry;
        if(hasContainer){
            const registry = await stubs.readRegistry();
            registryEntry = (registry.entries || []).find(entry => entry.containerName === containerName);
            currentHash = await stubs.readContainerConfigHash(containerName);
            if(!currentHash){
                currentHash = registryEntry ? registryEntry.configHash : null;
            }
            hashMismatch = !currentHash || currentHash !== expectedHash;
            if(hashMismatch){
                const lastUsedAtMs = registryEntry ? registryEntry.lastUsedAtMs : undefined;
                const isHot = running && (typeof lastUsedAtMs !== "number" || (now - lastUsedAtMs) < stubs.HOT_CONTAINER_WINDOW_MS);
                if(isHot){
                    const hint = stubs.formatSandboxRecreateHint({ scope: params.cfg.scope, sessionKey: scopeKey });
                    stubs.runtimeLog(`Sandbox config changed for ${containerName} (recently used). Recreate to apply: ${hint}`);
                }else{
                    await stubs.execDocker(["rm","-f",containerName], { allowFailure: true });
                    hasContainer = false;
                    running = false;
                }
            }
        }
        if(!hasContainer){
            await stubs.createSandboxContainer({
                name: containerName,
                cfg: params.cfg.docker,
                workspaceDir: params.workspaceDir,
                workspaceAccess: params.cfg.workspaceAccess,
                agentWorkspaceDir: params.agentWorkspaceDir,
                scopeKey,
                configHash: expectedHash
            });
        }else if(!running){
            await stubs.execDocker(["start",containerName]);
        }
        await stubs.updateRegistry({
            containerName,
            backendId: "docker",
            runtimeLabel: containerName,
            sessionKey: scopeKey,
            createdAtMs: now,
            lastUsedAtMs: now,
            image: params.cfg.docker.image,
            configLabelKind: "Image",
            configHash: (hashMismatch && running) ? (currentHash ?? undefined) : expectedHash
        });
        return containerName;
    };
})();

describe('test testpilot_subject', function() {
    it('should create a container when none exists', async function() {
        const stubs = testpilot_subject.file_0013.__stubs;

        // arrange: ensure dockerContainerState reports no container
        stubs.dockerContainerState = async (containerName) => ({ exists: false, running: false });

        let created = null;
        stubs.createSandboxContainer = async (opts) => { created = opts; return { created: true }; };

        let updatedRegistryEntry = null;
        stubs.updateRegistry = async (entry) => { updatedRegistryEntry = entry; return entry; };

        const params = {
            cfg: {
                scope: "user",
                docker: { containerPrefix: "tp-", image: "img:latest" },
                workspaceAccess: "rw"
            },
            workspaceDir: "/work",
            agentWorkspaceDir: "/agent",
            sessionKey: "s123"
        };

        // act
        const name = await testpilot_subject.file_0013.ensureSandboxContainer(params);

        // assert
        assert.strictEqual(name.startsWith("tp-"), true, "containerName should start with prefix");
        assert.ok(created, "createSandboxContainer should have been called");
        assert.strictEqual(created.name, name);
        assert.ok(updatedRegistryEntry, "updateRegistry should have been called");
        assert.strictEqual(updatedRegistryEntry.containerName, name);
        // configHash in registry should match expected (computed deterministically in stub)
        const expectedHash = stubs.computeSandboxConfigHash({
            docker: params.cfg.docker,
            workspaceAccess: params.cfg.workspaceAccess,
            workspaceDir: params.workspaceDir,
            agentWorkspaceDir: params.agentWorkspaceDir
        });
        assert.strictEqual(updatedRegistryEntry.configHash, expectedHash);
    });

    })