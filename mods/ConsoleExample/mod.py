"""Native console + persistent Python + mod-owned command example."""


class Mod:
    def enable(self, session):
        self.session = session
        self.calls = 0
        self.greeting = session.console.register('sdk.hello', self.hello, owner=self)

    def hello(self, arguments=''):
        self.calls += 1
        return f'Hello from ConsoleExample: {arguments} (call {self.calls})'

    def some_function(self):
        return self.hello('Python mod API')

    def disable(self):
        if getattr(self, 'greeting', None) is not None:
            self.greeting.remove()
        self.greeting = None
        self.session = None
