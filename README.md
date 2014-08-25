# tornwrap [![Build Status](https://secure.travis-ci.org/stevepeak/tornwrap.png)](http://travis-ci.org/stevepeak/tornwrap) [![codecov.io](https://codecov.io/github/stevepeak/tornwrap/coverage.png)](https://codecov.io/github/stevepeak/tornwrap)

```sh
pip install tornwrap
```

# Usage

| [Basic WWW Auth](#basic-auth) | [Rate Limited](#rate-limited) |               [Validated](#validated)               |
| ----------------------------- | ----------------------------- | --------------------------------------------------- |
| `@authenticated`              | `@ratelimited`                | `@validated`                                        |
| via `Basic realm=Restricted`  | w/ user and guest usage rates | using [valideer](https://github.com/podio/valideer) |


## Basic Auth

```py
from tornwrap import authenticated

class Handler(RequestHandler):
    def get_authenticated_user(self, user, password):
        if user == "user" and password == "password":
            # get your customer object
            return dict(id="1", name="name")
        return None

    @authenticated
    def get(self):
        self.write("Hello, world!")
```

## Rate Limited
> Requires `redis`

```py
from tornwrap import ratelimited

class Handler(RequestHandler):
    def initialize(self, redis):
        self.redis = redis # required

    @ratelimited(guest=(1000, 3600), user=(10000, 1800))
    def get(self):
        # users get 10k requests every 30 min
        # guests get 1k every 1h
        self.write("Hello, world!")

    def was_rate_limited(self, tokens, remaining, ttl):
        # notice we do not raise HTTPError here
        # because it will reset headers, which kinda sucks
        self.set_status(403)
        self.finish({"message": "You have been rate limited."})
```

## Validated
> Uses [valideer](https://github.com/podio/valideer)

```py
from tornwrap import validated

class Handler(RequestHandler):
    @validated({"+name":"string"})
    def get(self):
        # all your data is in `self.validated`
        self.finish("Hello, %s!" % self.validated.get('name', 'nobody'))
```
