let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.buildSingleSubagentBlock - existence and type', function(done) {
        // Locate the constructor/prototype safely
        assert.ok(testpilot_subject, 'module testpilot_subject must be present');
        assert.ok(testpilot_subject.file_0003, 'module must expose file_0003');
        const proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype must exist');

        assert.strictEqual(typeof proto.buildSingleSubagentBlock, 'function',
            'buildSingleSubagentBlock should be a function on the prototype');
        done();
    });

    })