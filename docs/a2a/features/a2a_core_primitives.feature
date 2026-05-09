Feature: A2A Core Generative Primitives
  As an external autonomous agent
  I want to invoke the Creative Studio over the A2A protocol
  So that I can generate foundational media assets like images and video

  Background:
    Given the Creative Studio is running with A2A REST endpoints exposed
    And I have a valid A2A_AGENT_TOKEN mapped to a human user director@example.com

  Scenario: Successful Image Generation via a2acli
    When I execute the command a2acli send --skill generate_media --input {"text":"A futuristic city"} --token <TOKEN>
    Then the CLI should stream a status update Processing prompt...
    And the CLI should exit with code 0
    And the final artifact should contain a valid GCS URI ending in .png
    And the asset should be visible in the Firestore library for director@example.com

  Scenario: Graceful Failure on Invalid Token
    When I execute the command a2acli send --skill generate_media --input {"text":"A futuristic city"} --token INVALID_TOKEN
    Then the server should return a 401 Unauthorized A2A error
    And the CLI should exit with a non-zero code

  Scenario: Video Generation with Reference Image via Apex Client
    Given I am connected to the Creative Studio agent in the Apex Flutter app
    When I send a message to the generate_media skill with text Animate this and a reference image URI
    Then the Apex chat bubble should display Generating video...
    And after processing, a native video player widget should render the resulting GCS URI
