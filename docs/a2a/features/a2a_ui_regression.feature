Feature: UI Regression Testing via Riptide (Computer Use Agent)
  As a QA Agent (Riptide)
  I want to visually navigate the GenMedia Creative Studio web application
  So that I can ensure the Services Layer refactoring (Phase 0) caused no UI regressions

  Background:
    Given the GenMedia Creative Studio is running locally on port 8080
    And I navigate to "http://localhost:8080"
    And the page title contains "GenMedia Creative Studio"

  Scenario: Generate an Image in Banana Studio
    Given I click the "Banana Studio" navigation link
    And I wait for the text "Type a prompt or add images" to appear
    When I click the textarea labeled "Prompt"
    And I type "A cinematic shot of a neon coffee mug"
    And I click the button with text "Generate Images"
    Then I should see the "Generating Images..." loading spinner
    And after waiting for the spinner to disappear
    Then I should see a generated image rendering in the right column
    And I should see a "Resolution:" pill below the image
    And I should see the "Actions" section appear with a "Continue" button

  Scenario: Verify C2PA Manifest is Attached to Generated Image
    Given I have successfully generated an image in Banana Studio
    When I look at the top right corner of the generated image
    Then I should see the "Content Credentials" info icon (info_outline)
    When I click the "Content Credentials" icon
    Then I should see a dialog or tooltip containing "AI-Generated" or "Google DeepMind"

  Scenario: Generate a Video via Veo
    Given I click the "Veo Video Generation" navigation link
    When I click the textarea labeled "Prompt"
    And I type "A drone flying through a canyon"
    And I click the button with text "Generate Video"
    Then I should see the "Generating Video..." status
    And after waiting for the generation to complete
    Then a video player widget should appear on the screen

  Scenario: Verify Asset Appears in Library
    Given I click the "Library" navigation link
    And I wait for the media grid to load
    Then I should see the image "A cinematic shot of a neon coffee mug" in the first row of the grid
    And I should see the video "A drone flying through a canyon" in the grid
    When I click the thumbnail for "A cinematic shot of a neon coffee mug"
    Then a detail dialog should open
    And the dialog should display the prompt "A cinematic shot of a neon coffee mug"
    And the dialog should display the model name used for generation
