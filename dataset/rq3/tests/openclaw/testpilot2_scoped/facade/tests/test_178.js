let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0005.createProcessTool', function() {
    it('returns a tool object with expected shape', function() {
        const tool = testpilot_subject.file_0005.createProcessTool({});
        assert.ok(tool && typeof tool === 'object', 'tool should be an object');
        assert.strictEqual(tool.name, 'process', 'tool.name should be "process"');
        assert.strictEqual(tool.label, 'process', 'tool.label should be "process"');
        assert.ok(typeof tool.description === 'string' && tool.description.length > 0, 'tool.description should be a non-empty string');
        assert.ok(tool.parameters, 'tool.parameters should be present');
        assert.ok(typeof tool.execute === 'function', 'tool.execute should be a function');
    });

    })