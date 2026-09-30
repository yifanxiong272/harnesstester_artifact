let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: shallow deep-equal for arrays (order-sensitive)
    function arrayEquals(a, b) {
        if (!Array.isArray(a) || !Array.isArray(b)) return false;
        if (a.length !== b.length) return false;
        for (let i = 0; i < a.length; i++) {
            if (a[i] !== b[i]) return false;
        }
        return true;
    }

    // Helper: try to determine whether a candidate value matches the provided text/images
    function candidateMatches(candidate, text, images) {
        if (candidate === text) return true; // stored as raw string
        if (candidate && typeof candidate === 'object') {
            // possible text fields to check
            const textFields = ['text', 'message', 'body', 'content', 'msg'];
            let textMatch = false;
            for (let f of textFields) {
                if (Object.prototype.hasOwnProperty.call(candidate, f) && candidate[f] === text) {
                    textMatch = true;
                    break;
                }
            }
            // also allow if object has a single primitive value equal to text
            if (!textMatch) {
                // check if object looks like {0: "text"} or similar (unlikely), skip
                // if text is empty string, still allow an explicit property
            }

            if (!textMatch) return false;

            // if images are provided, check for images-like property
            if (images !== undefined) {
                const imagesFields = ['images', 'imgs', 'attachments', 'pictures'];
                for (let f of imagesFields) {
                    if (Object.prototype.hasOwnProperty.call(candidate, f)) {
                        if (arrayEquals(candidate[f], images)) return true;
                        // sometimes stored as array of objects with url fields
                        if (Array.isArray(candidate[f]) && Array.isArray(images)) {
                            // check element-wise string equality if images are strings
                            const simpleA = candidate[f].every(el => typeof el === 'string');
                            const simpleB = images.every(el => typeof el === 'string');
                            if (simpleA && simpleB && arrayEquals(candidate[f], images)) return true;
                        }
                    }
                }
                // images expected but no images property matched -> fail
                return false;
            }

            // images not provided, having matched text is enough
            return true;
        }
        return false;
    }

    // Recursively traverse an object to find any array element or property matching our message
    function findMessageInStructure(root, text, images, maxDepth = 6) {
        const seen = new WeakSet();
        function recur(obj, depth) {
            if (obj === null || typeof obj !== 'object' || depth > maxDepth) return false;
            if (seen.has(obj)) return false;
            seen.add(obj);

            if (Array.isArray(obj)) {
                for (let el of obj) {
                    if (candidateMatches(el, text, images)) return true;
                    if (typeof el === 'object' && el !== null) {
                        if (recur(el, depth + 1)) return true;
                    }
                }
            } else {
                // check this object as a possible candidate
                if (candidateMatches(obj, text, images)) return true;
                for (let key of Object.keys(obj)) {
                    let val = obj[key];
                    if (candidateMatches(val, text, images)) return true;
                    if (typeof val === 'object' && val !== null) {
                        if (recur(val, depth + 1)) return true;
                    }
                }
            }
            return false;
        }
        return recur(root, 0);
    }

    it('should store a message with text and images somewhere in the instance after addMessage', function(done) {
        let svc = new testpilot_subject.file_0012.MessageQueueService();
        let text = 'hello world ' + Date.now();
        let images = ['img1.png', 'img2.png'];
        let ret;
        try {
            ret = svc.addMessage(text, images);
        } catch (err) {
            // If the implementation throws synchronously, fail the test
            return done(err);
        }

        // support promise-returning implementations
        if (ret && typeof ret.then === 'function') {
            ret.then(() => {
                let found = findMessageInStructure(svc, text, images);
                assert.ok(found, 'Expected to find the message with images inside the service instance');
                done();
            }).catch(done);
            return;
        }

        let found = findMessageInStructure(svc, text, images);
        assert.ok(found, 'Expected to find the message with images inside the service instance');
        done();
    });

    })