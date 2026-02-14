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

---

[^1]: Not actually patented. Why did I even say that? Please don't sue me, Taco Bell. I have great fucking lawyers you don't want the smoke. Fuck off.
