var jsdom = require('jsdom');
var should = require('should');
global.window = require('./emulate_dom.js');

document = window.document;
raw_survey = null;
L = window.L;
_ = window._;
$ = window.$;
alert = window.alert;
setInterval = function(hey, you) {  } //console.log('pikachu'); }
console = window.console;
Image = window.Image;
localStorage = {};

var mah_code = require('../static/app.js');
var App = mah_code.App;
var Survey = mah_code.Survey;
var Widgets = mah_code.Widgets;


// User interaction, "trigger" tests
describe('User next/prev tests', function(done) {

    before(function(done) {
        done();
    });

    beforeEach(function(done) {
        raw_survey = require('./fixtures/survey.json');
        App.init(raw_survey)
        done();
    });

    afterEach(function(done) {
        $("page_nav__next").off('click'); //XXX Find out why events are cached
        $("page_nav__prev").off('click');
        raw_survey = null;
        localStorage = {};
        done();
    });

    it('should move from question 0 to 1 when next is clicked', 
        function(done) {
            var survey = App.survey;
            var questions = survey.questions;

            var first_question = questions[0];
            var second_question = questions[1];

            first_question.should.equal(survey.current_question);

            $(".page_nav__next").trigger("click");

            first_question.should.not.equal(survey.current_question);
            second_question.should.equal(survey.current_question);

            done();
        });

    it('should move from last question to submit page when next is clicked',
        function(done) {
            var survey = App.survey;
            var questions = survey.questions;

            var last_question = questions[questions.length - 1];
            
            survey.render(last_question);
            last_question.should.equal(survey.current_question);

            $(".page_nav__next").trigger("click");

            // current question should remain the same on submitters page
            last_question.should.equal(survey.current_question);
            $(".question__title").html().trim()
                .should.equal("That's it, you're finished!");

            done();
        });

    it('should move from question 0 to nowhere when prev is clicked', 
        function(done) {
            var survey = App.survey;
            var questions = survey.questions;

            var first_question = questions[0];

            first_question.should.equal(survey.current_question);
            var title = $(".question__title").html();

            $(".page_nav__prev").trigger("click");
            first_question.should.equal(survey.current_question);
            $(".question__title").html().trim().should.equal(title);

            done();
        });

    it('should move from submit page to current question when prev is clicked', 
        function(done) {
            var survey = App.survey;
            var questions = survey.questions;
            
            var last_question = questions[questions.length - 1];
            survey.current_question = last_question;
            var title = "another note";

            // render submit page
            survey.next(1);
            last_question.should.equal(survey.current_question);

            // Now move back
            $(".page_nav__prev").trigger("click");
            last_question.should.equal(survey.current_question);
            $(".question__title").html().trim().should.match(title);
            done();
        });
});

describe('User submission tests', function(done) {
    before(function(done) {
        done();
    });


    beforeEach(function(done) {
        raw_survey = require('./fixtures/survey.json');
        localStorage.name = 'viktor sucks';
        App.init(raw_survey);
        done();
    });

    afterEach(function(done) {
        raw_survey = null;
        localStorage = {};
        done();
    });

    it('should preload submitter name', 
        function(done) {
            var survey = App.survey;
            var questions = survey.questions;
            var name = App.submitter_name;
            
            survey.render(undefined);
            $(".question__title").html().trim()
                .should.equal("That's it, you're finished!");

            $(".name_input").val()
                .should.equal(name);

            done();
        });

    it('should update submitter name', 
        function(done) {
            var survey = App.survey;
            var questions = survey.questions;
            var name = App.submitter_name;
            var new_name = '2chains'
            
            survey.render(undefined);
            $(".question__title").html().trim()
                .should.equal("That's it, you're finished!");

            $(".name_input").val(new_name)
            $(".name_input").trigger('keyup');

            // No references to old name
            $(".name_input").val()
                .should.not.equal(name);

            localStorage.name.should.not.equal(name);
            App.submitter_name.should.not.equal(name);

            // all the references
            localStorage.name.should.equal(new_name);
            $(".name_input").val().should.equal(new_name);
            App.submitter_name.should.equal(new_name);

            done();
        });
});
