Feature: Connecting to nrepl

    Scenario: Can connect to nrepl on localhost using nrepl URL
    Given a headless nrepl has been started on localhost
    When a connection is opened to 'nrepl://localhost:port/'
    Then a 'SessionContainer' is returned in 'connection'
