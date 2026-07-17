Have you ever worried that your code is too *boring*?

Did you feel inspired by that [scene](https://www.youtube.com/watch?v=uxKmDWDUZ5A) in The Social Network where those guys were ripping shots while they were ripping code?

Are you thinking to yourself RIGHT NOW "wow I'd love to get the booze flowing while I pump out line after line of intoxicated programming *beauty* but there's no way of being 100% sure that my codebase is protected from the dangers of sobriety"?

You're so stupid!!! The answer is here!

Introducing:

# BACStop: The git hook that keeps the party going!

**What it is:**
A git hook that forces you to take a BAC test and stops you in your goddam tracks from pushing any code if you aren't over the legal limit. It's sort of like the sobriety checkpoints they do to catch drunk drivers except it works in reverse. And also for coders. You get it.

**What it isn't:**
Going to let you write boring, dumb, and **ugly** code like what's probably permeating your old codebase! 🤮

**What you are:**
About to have a great time and write so much functional and sexy code!!!

---

## How does it work??

Glad you asked! The BACStopper comes in three patented[^1] flavors:

> 🟢 **Verde** 🟢
>
> The chillest level. Verde mode will check your BAC level but if it's not up to snuff he'll let it slide.

> 🌶️ **Hot** 🌶️
>
> The hard stopper. Hot mode will check your BAC level and won't even let you THINK about pushing that code if you're not drunk enough.

> 🔥🔥🔥 **DIABLO** 🔥🔥🔥
>
> The agent of chaos. Diablo doesn't fuck around. If you're not over the limit when you try to push that code then not only are you for sure not pushing that code but he will also NUKE all your changes. FOREVER. Not for the faint of heart.

---

## Boring dumb stuff about how to actually use it that I'm just going to let AI write because I can't be bothered but that you actually will find useful and probably need to know:

### How to install it

You need Python 3.8+ and a [BACtrack C8 Keychain Breathalyzer](https://a.co/d/0gD5uZdR). That's the only device this has been built and tested for.

```
pip install -e .
```

That's it.

### How to use it

Hook it up to whichever repo you want:

```
bactrack install --repo /path/to/your/repo --spice hot
```

Options:
- `--spice` — `verde`, `hot`, or `diablo` (default: `hot`)
- `--hook` — `pre-commit` or `pre-push` (default: `pre-push`)
- `--threshold` — BAC % to enforce (default: `0.00`)

To remove it:

```
bactrack uninstall --repo /path/to/your/repo
```

### Output

When the hook fires, you'll see something like this:

```
  ╔══════════════════════════════════════╗
  ║            BACstop Check             ║
  ╠══════════════════════════════════════╣
  ║  Hook:      pre-push                 ║
  ║  Spice:     hot                      ║
  ║  Threshold: 0.00%                    ║
  ╚══════════════════════════════════════╝
```

Then it connects to your breathalyzer, walks you through the test, and either lets you through or shuts you down depending on your spice level.

### CLI vs hook

The hook runs automatically on commit/push. But you can also use it standalone:

- `bactrack test` — take a breath test with a fancy UI (just for fun)
- `bactrack check` — run a BAC check and get an exit code (what the hook uses under the hood)
- `bactrack info` — see if your breathalyzer is connected

### Run a test from the CLI

To verify Bluetooth discovery, connection, and the complete breath-test flow
without running the HTTP server or installing a git hook:

```sh
bactrack test
```

Keep the BACtrack device nearby and available for pairing, then follow the
countdown and blow prompts. For plain terminal output, which is useful over SSH
or when diagnosing the device on a server, disable the interactive UI:

```sh
bactrack test --no-ui
```

The command prints the final BAC result or a device/test failure. Discovery and
connection errors exit nonzero. Use `bactrack test --help` to see all options.

### Local HTTP API

Start the platform-agnostic local server with:

```sh
bactrack serve
```

It listens on `127.0.0.1:8000` by default. Use `--host` and `--port` to change
the bind address, for example `bactrack serve --host 0.0.0.0 --port 8080`.
Binding outside localhost exposes control of the Bluetooth device to the network,
so apply your own network access controls when doing so.

The API keeps test state in memory. Restarting the process clears prior tests,
and only one test can be active at a time.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Check that the API process is running |
| `POST` | `/tests` | Start a test and return `202 Accepted` immediately |
| `GET` | `/tests/{test_id}` | Read the complete current test state |
| `GET` | `/tests/{test_id}/events` | Stream complete state snapshots as Server-Sent Events |

Start a test without metadata:

```sh
curl -X POST http://127.0.0.1:8000/tests
```

Metadata is optional JSON data that is stored and returned without being
interpreted:

```sh
curl -X POST http://127.0.0.1:8000/tests \
  -H 'Content-Type: application/json' \
  -d '{"metadata":{"request_id":"example-42","initiator":"workstation"}}'
```

The response contains a unique `test_id`. Use it to poll the test:

```sh
curl http://127.0.0.1:8000/tests/TEST_ID
```

Or consume live updates with SSE. The stream sends `state` events as status or
notification data changes, then one `terminal` event and closes:

```sh
curl -N http://127.0.0.1:8000/tests/TEST_ID/events
```

Statuses are `scanning`, `connected`, `countdown`, `blow`, `analyzing`,
`complete`, `cancelled`, `blow_error`, `timeout`, or `error`. Each response also
contains the latest raw notification, notification history, and the complete raw
result packet when one was received.

An external automation process can stay generic: send `POST /tests`, retain the
returned `test_id`, and either poll the corresponding test resource or listen to
its event stream until a terminal status arrives. It can then use `bac`, `error`,
and its own returned `metadata` according to that system's local policy.

---

[^1]: Not actually patented. Why did I even say that? Please don't sue me, Taco Bell. I have great fucking lawyers you don't want the smoke. Fuck off.
