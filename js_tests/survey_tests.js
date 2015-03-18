var jsdom = require('jsdom');
var should = require('should');
var assert = require('assert');
global.window = require('./emulate_dom.js');

document = window.document;
L = window.L;
_ = window._;
$ = window.$;
alert = window.alert;
setInterval = function(hey, you) {  } //console.log('pikachu'); }
console = window.console;
Image = window.Image;
navigator = window.navigator;
localStorage = {};
setTimeout = function(cb, time) { cb(); };
btoa = function(str) { return ''; }; // w.e we don't need to post anyway

var mah_code = require('../dokomoforms/static/app.js');
var App = mah_code.App;
var Survey = mah_code.Survey;
var Widgets = mah_code.Widgets;

var survey = null;

// Most important tests, survey functions
describe('Survey unit and regression tests', function(done) {
    before(function(done) {
        done();
    });

    beforeEach(function(done) {
        $.mockjax.clear();
        localStorage = {};
        localStorage.setItem = function(id, data) {
            localStorage[id] = data;
        }

        App.facilities = [];
        App.unsynced_facilities = {};

        done();
    });

    afterEach(function(done) {
        $(".page_nav__next").off('click'); //XXX Find out why events are cached
        $(".page_nav__prev").off('click');
        $(".message").clearQueue().text("");
        $('.content').empty();
        survey = null;
        done();
    });
    
    after(function(done) {
        done();
    });

    it('getFirstResponse: should return first non empty response',
        function(done) {
            var questions = [
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 1
                },
            ];

            survey = new Survey("id", 0, questions, {});

            // empty
            should(survey.getFirstResponse(questions[0])).match(null);
            // O value
            questions[0].answer = [{}, {response:0}];
            should(survey.getFirstResponse(questions[0])).match(0);;
            // some value
            questions[0].answer = [{response:1}, {}];
            should(survey.getFirstResponse(questions[0])).match(1);
            // some value doubled
            questions[0].answer = [{response:1}, {response: 2}];
            should(survey.getFirstResponse(questions[0])).match(1);
            // empty string
            questions[0].answer = [{response:""}];
            should(survey.getFirstResponse(questions[0])).match("");

            done();

        });
    
    it('getFirstResponse: should return null if theres no valid text input',
        function(done) {
            var questions = [
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "text",
                    logic: {},
                    sequence_number: 1
                },
            ];

            survey = new Survey("id", 0,  questions, {});

            // empty
            should(survey.getFirstResponse(questions[0])).match(null);
            // empty string
            questions[0].answer = [{response:Widgets._validate("text", "")}];
            should(survey.getFirstResponse(questions[0])).match(null);

            done();

        });

    
    // Note answer field can only be populated with data returned from widget._validate normally
    it('next: should enforce required questions',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "text",
                    logic: {required: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state shouldn't change
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);
            
            // state SHOULD change
            questions[0].answer = [{response: Widgets._validate("text", "yo")}];
            survey.next(NEXT);
            questions[0].should.not.equal(survey.current_question);
            questions[1].should.equal(survey.current_question);

            done();

        });
    
    it('next: should enforce required correctly for falsy response 0',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "integer",
                    logic: {required: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state shouldn't change
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);
            
            // state SHOULD change
            questions[0].answer = [{response:0}];
            survey.next(NEXT);
            questions[0].should.not.equal(survey.current_question);
            questions[1].should.equal(survey.current_question);

            done();

        });
    
    it('next: should enforce required correctly for falsy response ""',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "text",
                    logic: {required: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state shouldn't change
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);
            
            // state SHOULDNT change
            questions[0].answer = [{response: Widgets._validate("text", "")}];
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);

            done();

        });
    
    it('next: should enforce required correctly for invalid input to decimal',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "decimal",
                    logic: {required: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state shouldn't change
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);
            
            // state SHOULDNT change
            questions[0].answer = [{response: Widgets._validate("decimal", "bs")}];
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);


            done();

        });
    
    it('next: should enforce required correctly for invalid input to date',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "date",
                    logic: {required: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state shouldn't change
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);
            
            // state SHOULDNT change
            //questions[0].answer = ["date"];
            //survey.next(NEXT);
            //questions[0].should.equal(survey.current_question);
            //questions[1].should.not.equal(survey.current_question);
            //XXX VALIDATION FOR TIME NOT DONE;


            done();

        });
    
    it('next: should enforce required correctly for invalid input to time',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "time",
                    logic: {required: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state shouldn't change
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);
            
            // state SHOULDNT change
            //questions[0].answer = ["time"];
            //survey.next(NEXT);
            //questions[0].should.equal(survey.current_question);
            //questions[1].should.not.equal(survey.current_question);
            //XXX: VALIDATION FOR DATE NOT ENFORCED;


            done();

        });
    
    it('next: should enforce required for empty dont-know response',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "date",
                    logic: {with_other: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state SHOULDNT change
            questions[0].answer = [{response:"", is_other: true}]; // didn't fill out real response
            survey.next(NEXT);
            questions[0].should.equal(survey.current_question);
            questions[1].should.not.equal(survey.current_question);

            done();

        });
    
    it('next: should not enforce required for filled out dont-know response',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "date",
                    logic: {with_other: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state SHOULD change
            questions[0].answer = [{response:"viktor is a dingus", is_other: true}];
            survey.next(NEXT);
            questions[0].should.not.equal(survey.current_question);
            questions[1].should.equal(survey.current_question);

            done();

        });
    
    it('next: should not enforce required for no response with_other questions',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "date",
                    logic: {with_other: true},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            // state should change
            questions[0].answer = [];
            survey.next(NEXT);
            questions[0].should.not.equal(survey.current_question);
            questions[1].should.equal(survey.current_question);
            
            done();

        });
    
    it('next: should follow sequence number ordering not list ordering',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "time",
                    logic: {},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: 4,
                    type_constraint_name: "text",
                    logic: {},
                    sequence_number: 3
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 4
                },
                {
                    question_to_sequence_number: 3,
                    type_constraint_name: "decimal",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            questions[0].should.equal(survey.current_question);

            survey.next(NEXT);
            questions[3].should.equal(survey.current_question);
            
            survey.next(NEXT);
            questions[1].should.equal(survey.current_question);

            survey.next(NEXT);
            questions[2].should.equal(survey.current_question);
            
            survey.next(PREV);
            questions[1].should.equal(survey.current_question);

            survey.next(PREV);
            questions[3].should.equal(survey.current_question);

            survey.next(PREV);
            questions[0].should.equal(survey.current_question);
            done();

        });

    it('next: should follow new paths when answer branches',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "time",
                    logic: {},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: 4,
                    type_constraint_name: "text",
                    logic: {},
                    sequence_number: 3
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "text",
                    logic: {},
                    sequence_number: 5
                },
                {
                    question_to_sequence_number: 5,
                    type_constraint_name: "text",
                    logic: {},
                    sequence_number: 4
                },
                {
                    question_to_sequence_number: 3,
                    type_constraint_name: "text", //code doesnt assert that its multiple choice
                    logic: {},
                    branches: [
                        {
                            question_choice_id: "end", // pretend this is a uuid
                            to_sequence_number: 5,
                        },
                        {
                            question_choice_id: "skip", // fake uuid
                            to_sequence_number: 4,
                        }
                    ],
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            var brancher = questions[4];
            var next = questions[1];
            var end = questions[2];
            var skip = questions[3];

            questions[0].should.equal(survey.current_question);
            survey.next(NEXT);

            // assert we are at branching question
            brancher.should.equal(survey.current_question);
            // follows normal seq path
            survey.next(NEXT);
            next.should.equal(survey.current_question);
            // assert we are back
            survey.next(PREV);
            brancher.should.equal(survey.current_question);
            // branch to end 
            brancher.answer = [{response:"end"}];
            survey.next(NEXT); 
            end.should.equal(survey.current_question);
            // come back
            survey.next(PREV);
            brancher.should.equal(survey.current_question);
            // branch to skip 
            brancher.answer = [{response:"skip"}];
            survey.next(NEXT); 
            skip.should.equal(survey.current_question);
            // come back again fine
            survey.next(PREV);
            brancher.should.equal(survey.current_question);
            

            done();

        });

    it('submit: empty submission',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "time",
                    logic: {},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            survey = new Survey("id", 0, questions, {});
            survey.submit();
            $('.message').text().should.match("Submission failed, No questions answer in Survey!");
            done();

        });

    it('submit: basic submission',
        //XXX: Fake response so that this doesn't 404
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: 2,
                    type_constraint_name: "text",
                    logic: {},
                    sequence_number: 1
                },
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "integer",
                    logic: {},
                    sequence_number: 2
                },
            ];

            $.mockjax({
                  url: '',
                  status: 200,
                  onAfterSuccess: function() { 
                    $('.message').text().should.match('Survey submitted!'); 
                    done();
                  },
                  onAfterError: function() { 
                      assert(false, "Failed to catch post correctly"); 
                  },
                  responseText: {
                      status: "success",
                  }
            });


            survey = new Survey("id", 0, questions, {});
            questions[0].answer = [{response:"hey baby"}];
            survey.submit();

        });


    it('submit: facility submission',
        function(done) {
            var NEXT = 1;
            var PREV = -1;
            var questions = [
                {
                    question_to_sequence_number: -1,
                    type_constraint_name: "facility",
                    logic: {},
                    answer: [],
                    question_title: "fac",
                    sequence_number: 1
                },
            ];

            // Preload some facilities;
            App.unsynced_facilities[1] = {
                'name': 'New Facility', 'uuid': 1, 
                'properties' : {'sector': 'health'},
                'coordinates' : [40.01, 70.01]
            };


            var url = "http://staging.revisit.global/api/v0/facilities.json" // install revisit server from git
            $.mockjax({
                  url: url,
                  status: 200,
                  onAfterSuccess: function() { 
                    $('.message').text().should.match('Facility Added!'); 
                    //XXX async can hang if js error is encountered
                    Object.keys(App.unsynced_facilities).should.have.length(0);
                    App.facilities.should.have.length(1);
                    done();
                  },
                  onAfterError: function() { 
                      assert(false, "Failed to catch revisit correctly"); 
                      done();
                  },
                  responseText: {
                      status: "success",
                  }
            });
            
            $.mockjax({
                  url: '',
                  status: 200,
                  onAfterSuccess: function() { 
                  },
                  onAfterError: function() { 
                      assert(false, "Failed to catch post correctly"); 
                  },
                  responseText: {
                      status: "success",
                  }
            });


            survey = new Survey("id", 0, questions, {});
            questions[0].answer = [{response:{'id': 1, 'lat':40.01, 'lon':70.01 }}];
            survey.submit();

        });
});

