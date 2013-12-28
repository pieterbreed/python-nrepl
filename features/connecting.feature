Feature: Connecting to nrepl

    Scenario: Can connect to nrepl on localhost
    Given a headless nrepl has been started on localhost port 8080
    When a connection is created
    Then a replmanager is returned
