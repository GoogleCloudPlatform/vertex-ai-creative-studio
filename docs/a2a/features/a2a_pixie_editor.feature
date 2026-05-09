Feature: A2A Pixie Conversational Editor
  As an external orchestrator agent
  I want to converse with the Pixie persona
  So that I can plan and execute complex media compositing tasks

  Background:
    Given I am authenticated with the Creative Studio A2A endpoint
    And the pixie skill is available in the Agent Card

  Scenario: Multi-turn conversational planning
    Given I send a message to pixie asking I have a fast-paced video and a slow audio track, how should I cut them?
    Then the response should be conversational text advising on editing techniques
    And the response should NOT contain a media artifact
    And the task state should be completed

  Scenario: Stateful execution of a composition
    Given I have a multi-turn history where we discussed syncing an audio track
    When I send a follow-up message to pixie with the video URI, audio URI, and the command Execute the sync we discussed
    Then Pixie should stream a status update Running FFmpeg composition...
    And the final artifact should be a GCS URI of the composited video
    And the new asset should be tagged with agent_id: pixie in the Firestore library
