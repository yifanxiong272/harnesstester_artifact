let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0003.ToolCallComponent.prototype.buildStreamingPreview', function() {
    let originalDocument = global.document;
    let ToolCallComponent, buildPreview;

    // A minimal fake DOM to allow implementations that use document.createElement / createTextNode
    function makeFakeDocument() {
        return {
            createElement: function(tagName) {
                // simple element-like object
                return {
                    tagName: String(tagName).toUpperCase(),
                    children: [],
                    attributes: {},
                    innerHTML: '',
                    textContent: '',
                    appendChild: function(child) { this.children.push(child); },
                    setAttribute: function(name, value) { this.attributes[name] = value; },
                    getAttribute: function(name) { return this.attributes[name]; }
                };
            },
            createTextNode: function(text) {
                return { nodeType: 3, textContent: String(text) };
            },
            createDocumentFragment: function() {
                return { children: [], appendChild: function(c) { this.children.push(c); } };
            }
        };
    }

    before(function() {
        // ensure module shape is present
        assert.ok(testpilot_subject, 'testpilot_subject module must be present');
        assert.ok(testpilot_subject.file_0003, 'testpilot_subject.file_0003 must be present');
        ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
        assert.ok(ToolCallComponent, 'ToolCallComponent constructor must be present');
        buildPreview = ToolCallComponent.prototype.buildStreamingPreview;
    });

    beforeEach(function() {
        // install fake document so DOM-using implementations do not throw
        global.document = makeFakeDocument();
    });

    afterEach(function() {
        // restore original document
        global.document = originalDocument;
    });

    it('should exist and be a function', function() {
        assert.strictEqual(typeof buildPreview, 'function', 'buildStreamingPreview should be a function');
        // arity: should accept one argument according to signature buildStreamingPreview(streamText)
        assert.ok(buildPreview.length >= 1, 'function should accept at least one parameter');
    });

    })