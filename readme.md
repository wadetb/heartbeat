# Heartbeat utility

This simple Python 3 utility checks that servers are alive and responding. I use it with [Twilio](https://www.twilio.com/) to text me when one of my servers go down, for whatever reason.

It's invoked using `python3 heartbeat.py`, reads its configuration from a configuration file `heartbeat.yaml`, and saves its state in `.heartbeat.state.json`.

Example configuration file:

```yaml
tests:
  - http:
    name: Google
    url: https://www.google.com/

alerts:
  - twilio:
    account_sid: XXXXXXXXXXXXXX
    auth_token: XXXXXXXXXXXXXX
    from_number: +17775551212
    to_number: +12224443131
```

The configuration file is divided into two sections: **tests** and **alerts**.

## Tests configuration

Tests are checks that are performed when the `heartbeat` utility runs.
Any tests that fail will trigger alerts. Supported tests include `http`, `tcp`, and `shell`.

Common test configuration settings:

|||
|-|-|
|name|The name of the test, used in the default messages|
|down_message|Message sent when the test fails. Defaults to `$name is down`.|
|up_message|Message sent when the test passes after failing. Defaults to `$name is up`.|
|ignore_fail_count|Number of test failures ignored before sending an alert. Defaults to 0.|
|alert_period_hours|Number of hours between successive alerts while the test is still failing. Defaults to 1.0.|

### HTTP

`http` requests the given URL and confirms that the response status code is 200.

|||
|-|-|
|url|The URL to query, required. Must be HTTP or HTTPS.|
|headers|Dictionary of additional headers to send.|
|timeout|Stop waiting for a response after a given number of seconds.|

Example:

```yaml
- tests:
  - http:
    name: Home Assistant
    url: https://hass.local/api/
    headers:
      x-ha-access: XXXXXXXX
      Content-Type: application/json
```

### TCP

`tcp` opens a connection to the host and port and confirms that a connection is established.

|||
|-|-|
|host|Host name or IP address to connect to, required.|
|port|Port number to open, required.|
|timeout|Seconds to wait for a connection before timing out.|

Example:

```yaml
- tests:
  - tcp:
    name: SSH server
    host: my.server.io
    port: 22
```

### Shell

`shell` runs a command and confirm that the exit code is zero.

|||
|-|-|
|command|Command to execute using the current shell, required.|
|timeout|Seconds to wait for the child process to exit.|

Example:

```yaml
- tests:
  - shell:
    name: Internet connection
    command: curl https://www.google.com
```

## Alerts configuration

Alerts are notifications sent when tests fail. Supported alerts include `twilio` and `shell`.


### Gmail
sent alerts from gmail(Creating an [application specific password](https://security.google.com/settings/security/apppasswords) is required)
|||
|-|-|
|sent_from|gmail address, required|
|gmail_password|gmail's 3rd party password, required.|
|to|mail address sending to, required.|
|subject|The subject, required.|

### Twilio

`twilio` uses the Twilio REST API to send a text message. Sign up for a free account (including a SMS number) at https://www.twilio.com/. Note that repeated alerts can rack up charges once your trial is exhausted, so be careful with your test settings.

Note that the `twilio` module must be installed to use twilio alerts, using `pip install twilio`.

|||
|-|-|
|account_sid|Twilio account SID from the dashboard, required.|
|auth_token|Twilio auth token from the dashboard, required.|
|from_number|Twilio phone number from the dashboard, required.|
|to_number|Destination phone number, required.|

### Shell

`shell` runs a command using the current shell to deliver the alert.

|||
|-|-|
|command|Command to execute using the current shell, required.|

The alert message can be inserted into `command` using `$message`.

## Message value substitution

In a test's `up_message` and `down_message`, named values can be inserted using `$<name>`.

|||
|-|-|
|state|Current state of the test, either `passing` or `failing`.|
|fail_count|Number of consecutive failures.|
|last_pass_time|Time at which the test most recently passed.|
|last_fail_time|Time at which the test most recently failed.|

Additionally, any value from the test's configuration can be inserted using similar syntax.

Example:

```yaml
- tests:
  - http:
    name: My site
    url: http://test.org
    down_message: $name ($url) has been down since $last_pass_time.
```

# Installation

Run every minute via `crontab -e`:

```
* * * * * /usr/local/bin/python3 /home/me/heartbeat.py
```
