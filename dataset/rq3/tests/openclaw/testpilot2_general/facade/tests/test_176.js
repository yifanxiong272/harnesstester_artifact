let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0005.createProcessTool - metadata and shape', async function() {
        const tool = testpilot_subject.file_0005.createProcessTool({});
        // Basic shape checks
        assert.strictEqual(tool.name, 'process');
        assert.strictEqual(tool.label, 'process');
        assert.ok(typeof tool.description === 'string' && tool.description.length > 0);
        assert.ok(tool.parameters, 'parameters should be present');
        assert.ok(typeof tool.execute === 'function', 'execute should be a function');
    });

    })