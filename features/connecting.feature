Feature: Connecting to nrepl

    Scenario: Can connect to nrepl on localhost using nrepl URL
    Given a headless nrepl has been started on localhost
    When a connection is opened to 'nrepl://localhost:port/'
    Then a 'SessionContainer' is returned in 'connection'

    Scenario: Can create a new session from SessionContainer
    Given a headless nrepl has been started on localhost
    And a connection is opened to 'nrepl://localhost:port/'
    When a new session is requested
    Then a 'NREPLSession' is returned in 'session'
