#!/usr/bin/env python3
import datetime
import hashlib
import json
import time
import yaml

DATETIME_FORMAT = '%m/%d %H:%M'


def format_now():
    return datetime.datetime.now().strftime(DATETIME_FORMAT)


class Test:
    def __init__(self, owner, config):
        self.owner = owner
        self.config = config
        self.id = hashlib.sha256(json.dumps(config).encode()).hexdigest()
        self.down_message = config.setdefault('down_message', '$name is down, since $last_pass_time')
        self.up_message = config.setdefault('up_message', '$name is up')
        self.ignore_fail_count = config.setdefault('ignore_fail_count', 0)
        self.alert_period_hours = config.setdefault('alert_period_hours', 1.0)

    def get(self, key, default=None):
        if not self.id in self.owner.state:
            self.owner.state[self.id] = {}
        return self.owner.state[self.id].setdefault(key, default)

    def set(self, key, value):
        if not self.id in self.owner.state:
            self.owner.state[self.id] = {}
        self.owner.state[self.id][key] = value

    def expand_message(self, message):
        for key, value in self.config.items():
            message = message.replace('$' + key, str(value))
        if not self.id in self.owner.state:
            self.owner.state[self.id] = {}
        for key, value in self.owner.state[self.id].items():
            message = message.replace('$' + key, str(value))
        return message

    def do_pass(self):
        if self.get('state') != 'passing':
            self.owner.notify(self.expand_message(self.up_message))
            self.set('state', 'passing')
            self.set('first_pass_time', format_now())
            self.set('last_fail_alert_time', 0)
        self.set('name', self.config['name'])
        self.set('last_pass_time', format_now())
        self.set('fail_count', 0)

    def do_fail(self):
        fail_count = self.get('fail_count', 0) + 1
        self.set('name', self.config['name'])
        self.set('fail_count', fail_count)
        if fail_count > self.ignore_fail_count:
            if self.get('state') != 'failing':
                self.set('state', 'failing')
                self.set('first_fail_time', format_now())
            alert_time = time.time()
            last_alert_fail_time = self.get('last_fail_alert_time', 0)
            if alert_time - last_alert_fail_time >= self.alert_period_hours * 60 * 60:
                self.set('last_fail_alert_time', alert_time)
                self.owner.notify(self.expand_message(self.down_message))
        self.set('last_fail_time', format_now())


class ShellTest(Test):
    def __init__(self, owner, config):
        super().__init__(owner, config)
        import subprocess
        self.command = config['command']
        self.timeout = config.get('timeout')

    def run(self):
        import subprocess
        try:
            subprocess.run(self.command, shell=True, check=True, timeout=self.timeout)
        except subprocess.CalledProcessError:
            self.do_fail()
        else:
            self.do_pass()


class TCPTest(Test):
    def __init__(self, owner, config):
        super().__init__(owner, config)
        import socket
        self.host = config['host']
        self.port = config['port']
        self.timeout = config.get('timeout')

    def run(self):
        import socket
        try:
            with socket.create_connection((self.host, self.port), self.timeout) as sock:
                print('{}:{} OK'.format(self.host, self.port))
                sock.shutdown(socket.SHUT_RDWR)
        except OSError as err:
            print('{}:{} {}'.format(self.host, self.port, err))
            self.do_fail()
        else:
            self.do_pass()


class HTTPTest(Test):
    def __init__(self, owner, config):
        super().__init__(owner, config)
        import requests
        self.url = config['url']
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout')

    def run(self):
        import requests
        try:
            r = requests.get(self.url, headers=self.headers, timeout=self.timeout)
            print(self.url, r.status_code, r.reason)
            if r.status_code == 200:
                self.do_pass()
            else:
                self.do_fail()
        except Exception as e:
            self.do_fail()


TEST_PROVIDERS = [('shell', ShellTest), ('tcp', TCPTest), ('http', HTTPTest)]


class Alert:
    def __init__(self, config):
        pass


class ShellAlert(Alert):
    def __init__(self, config):
        super().__init__(config)
        import subprocess
        self.command = config['command']

    def send(self, message):
        import subprocess
        command = self.command.replace('$message', message)
        subprocess.run(command, shell=True, check=True)


class TwilioAlert(Alert):
    def __init__(self, config):
        super().__init__(config)
        import twilio
        self.account_sid = config['account_sid']
        self.auth_token = config['auth_token']
        self.from_number = config['from_number']
        self.to_number = config['to_number']

    def send(self, message):
        from twilio.rest import Client
        client = Client(self.account_sid, self.auth_token)
        client.api.account.messages.create(
            to=self.to_number, from_=self.from_number, body=message)


ALERT_PROVIDERS = [('shell', ShellAlert), ('twilio', TwilioAlert)]


class Heartbeat:
    def __init__(self):
        self.tests = []
        self.alerts = []
        self.state = {}

    def _load_tests(self, config):
        for test in config:
            for key, provider in TEST_PROVIDERS:
                if key in test:
                    self.tests.append(provider(self, test[key]))

    def _load_alerts(self, config):
        for alert in config:
            for key, provider in ALERT_PROVIDERS:
                if key in alert:
                    self.alerts.append(provider(alert[key]))

    def load_config(self):
        with open('heartbeat.yaml') as config_file:
            config = yaml.safe_load(config_file)
        self._load_tests(config['tests'])
        self._load_alerts(config['alerts'])

    def load_state(self):
        try:
            with open('.heartbeat.json') as state_file:
                self.state = json.load(state_file)
        except:
            self.state = {}

    def save_state(self):
        with open('.heartbeat.json', 'w') as state_file:
            json.dump(self.state, state_file)

    def notify(self, message):
        for alert in self.alerts:
            alert.send(message)

    def test(self):
        for test in self.tests:
            test.run()

    def run(self):
        self.load_config()
        self.load_state()
        self.test()
        self.save_state()


if __name__ == '__main__':
    heartbeat = Heartbeat()
    heartbeat.run()
