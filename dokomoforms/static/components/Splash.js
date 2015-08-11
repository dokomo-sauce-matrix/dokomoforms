var React = require('react');

var Card = require('./baseComponents/Card.js');
var BigButton = require('./baseComponents/BigButton.js');

/*
 * Splash page component
 * Renders the appropiate card for the main page
 *
 * props:
 *     @language: current survey language
 *     @surveyID: current survey id
 *     @buttonFunction: What to do when submit is clicked
 */
module.exports = React.createClass({
    getInitialState: function() {
        // Get all unsynced surveys
        var unsynced_surveys = JSON.parse(localStorage['unsynced'] || '{}');
        // Get array of unsynced submissions to this survey
        var unsynced_submissions = unsynced_surveys[this.props.surveyID] || [];

        return { 
            count: unsynced_submissions.length,
            online: navigator.onLine,
        }
    },

    // Force react to update
    update: function() {
        // Get all unsynced surveys
        var unsynced_surveys = JSON.parse(localStorage['unsynced'] || '{}');
        // Get array of unsynced submissions to this survey
        var unsynced_submissions = unsynced_surveys[this.props.surveyID] || [];

        this.setState({ 
            count: unsynced_submissions.length,
            online: navigator.onLine,
        });
    },

    buttonFunction: function(event) {
        if (this.props.buttonFunction)
            this.props.buttonFunction(event);

        // Get all unsynced surveys
        var unsynced_surveys = JSON.parse(localStorage['unsynced'] || '{}');
        // Get array of unsynced submissions to this survey
        var unsynced_submissions = unsynced_surveys[this.props.surveyID] || [];

        this.setState({ 
            count: unsynced_submissions.length,
            online: navigator.onLine,
        });

    },

    getCard: function() {
        var email = localStorage['submitter_email'] || "anon@anon.org";
        var title = this.props.surveyTitle[this.props.language];
        if (this.state.count) {
            if (this.state.online) {
                // Unsynced and online
                return (
                        <span>
                        <Card messages={[['You have ',  <b>{this.state.count}</b>, ' unsynced surveys.', ' Please submit them now.'], 
                            ]} type={"message-warning"}/>
                        <BigButton text={"Submit Completed Surveys"} buttonFunction={this.buttonFunction} /> 
                        </span>
                       )
            } else {
                // Unsynced and offline
                return (
                        <Card messages={[['You have ',  <b>{this.state.count}</b>, ' unsynced surveys.'], 
                            '',
                            'At present, you do not have a network connection — please remember to submit' 
                                + ' these surveys the next time you do have access to the internet.'
                        ]} type={"message-warning"}/>
                       )
            }
        } else {
            // No unsynced surveys
            return (
                    <Card messages={[['Hi ', <b>{email}</b>, ' and welcome to the ', {title}, <br/>], 
                        ['If you have any questions regarding the survey, please ', <u>contact the survey adminstrator</u>]]} 
                    type={"message-primary"}/>
                   )
        }
    },

    render: function() {
        return this.getCard()
    }
});
