let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const CodeIndexSearchService = testpilot_subject.file_0009.CodeIndexSearchService;

    function makeMocks(options = {}) {
        const {
            isFeatureEnabled = true,
            isFeatureConfigured = true,
            minScore = 0.1,
            maxResults = 10,
            currentState = "Indexed",
            embedderImpl,
            vectorStoreImpl
        } = options;

        const configManager = {
            isFeatureEnabled,
            isFeatureConfigured,
            currentSearchMinScore: minScore,
            currentSearchMaxResults: maxResults
        };

        let lastSetSystemState = null;
        const stateManager = {
            getCurrentStatus: () => ({ systemStatus: currentState }),
            setSystemState: (state, msg) => { lastSetSystemState = { state, msg }; }
        };

        const embedder = embedderImpl || {
            // default: returns a simple embedding
            createEmbeddings: async (arr) => {
                return { embeddings: [Array.from({length:4}, (_,i)=>i + 0.1)] };
            }
        };

        // vectorStoreImpl should be async function search(vector, prefix, minScore, maxResults)
        let capturedArgs = null;
        const vectorStore = vectorStoreImpl || {
            search: async (vector, prefix, minScoreArg, maxResultsArg) => {
                capturedArgs = { vector, prefix, minScoreArg, maxResultsArg };
                return [
                    { id: 'file1', score: 0.95 },
                    { id: 'file2', score: 0.9 }
                ];
            }
        };

        return {
            configManager,
            stateManager,
            embedder,
            vectorStore,
            getLastSetSystemState: () => lastSetSystemState,
            getCapturedVectorStoreArgs: () => capturedArgs
        };
    }

    it('throws if code index feature is disabled or not configured', async function() {
        const mocks = makeMocks({ isFeatureEnabled: false });
        const svc = new CodeIndexSearchService(mocks.configManager, mocks.stateManager, mocks.embedder, mocks.vectorStore);

        await assert.rejects(
            svc.searchIndex('query'),
            /Code index feature is disabled or not configured\./
        );

        // Ensure state was not changed to Error (this failure happens before try/catch)
        assert.strictEqual(mocks.getLastSetSystemState(), null);
    });

    })