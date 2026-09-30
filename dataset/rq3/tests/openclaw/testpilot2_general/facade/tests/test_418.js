let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0014.isToolResultMediaTrusted', function() {
    it('should return a boolean for a typical tool/result pair', function() {
        let toolName = 'screenshot';
        let result = {
            media: {
                type: 'image/png',
                data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA'
            },
            metadata: {
                width: 100,
                height: 50
            },
            // some implementations might use an explicit flag
            isTrusted: true
        };

        let out = testpilot_subject.file_0014.isToolResultMediaTrusted(toolName, result);
        assert.strictEqual(typeof out, 'boolean', 'expected a boolean result');
    });

    })