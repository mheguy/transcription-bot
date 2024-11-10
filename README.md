# transcription-bot

![transcriptionbot](https://cronitor.io/badges/ptDp2a/production/g39Jba1nK2_Hh3UVLqswolPPAPI.svg)

This tool creates transcripts for episodes of the podcast "the Skeptic's Guide to the Universe".<br>
This tool is a fan creation and is neither endorsed by nor associated with the creators of the podcast.<br>

## How it works

This explanation is targeted toward those who have no experience writing or reading code.<br>

### Transcription

We create a transcription of an episode. The transcription contains the words that were said as well as the time at which they were spoken.<br>
That looks a bit like this:

> 0:01.234 - And<br>
> 0:01.450 - that's<br>
> 0:01.750 - why<br>

For the sake of our demo, here are the words that we extracted without the timestamps.<br>

> And what's why taxes are so fascinating I'm not sure I agree alright, time for a quickie with Bob yes folks we're going to talk about lasers the pew pew kind?

The next layer is diarization. That tells us when a different person is speaking.<br>

> SPEAKER_01: 0:01-0:03<br>
> SPEAKER_04: 0:04-0:06<br>
> SPEAKER_03: 0:07-0:09<br>
> SPEAKER_02: 0:10-0:14<br>
> SPEAKER_05: 0:14-0:15<br>

We merge the transcription and the diarization:

> SPEAKER_01: And what's why taxes are so fascinating.<br>
> SPEAKER_04: I'm not sure I agree.<br>
> SPEAKER_03: Alright, time for a quickie with Bob.<br>
> SPEAKER_02: Yes folks we're going to talk about lasers.<br>
> SPEAKER_05: The pew pew kind?<br>

And then we apply voiceprints we have on file to identify the speakers.

> Evan: And what's why taxes are so fascinating.<br>
> Cara: I'm not sure I agree.<br>
> Steve: Alright, time for a quickie with Bob.<br>
> Bob: Yes folks we're going to talk about lasers.<br>
> Jay: The pew pew kind?<br>

At this point, the transcription is completed and we have what is internally called a "diarized transcript".<br>

### Segment Data Gathering

The bot has information about all the recurring segment types.<br>
But it needs to know what segments a particular episode contains.<br>

To figure this out, we need data.<br>
The two sources that we use for this data are the show notes web page, and the embedded lyrics in the episode mp3 file.<br>

By combining the data from those two sources, we know what segments the episode contains and the order they are in.<br>

### Segmenting the Transcript

To continue the example from above, let's say we know that this episode has a "Quickie" segment.<br>
The bot is programmed to look for the words "quickie with" to find the transition point into the segment.<br>
This enables us to break the full transcript into the episode segments.<br>

> Cara: I'm not sure I agree.<br>
> == Quickie with Bob: Lasers ==
> Steve: Alright, time for a quickie with Bob.<br>

We use templates to ensure that we match the desired formatting for the wiki.

#### When Segmenting is Tricky

It's tricky to identify transitions into news segments. We have no "key words" that reliably tell us when a transition is happening.<br>
So for this case, and as a fallback for all segment types when heuristics don't work, we send a chunk of transcript to GPT and ask it to identify the transition.<br>

### Other Odds and Ends

We download the image from the show notes page and upload it to the wiki. We add a caption that is generated by GPT
(this results in something pretty bland and not specific to the episode).<br>
We load the links to extract the article titles which are used in the references at the bottom of the wiki pages.<br>

## Development

The project uses Python 3.11 because many of the ML libraries have not yet adopted 3.12.<br>
Poetry is used to manage dependencies. `poetry install` will get you set up.<br>

There are a number of required env vars to run the tool. `dotenv` is set up, so we can place our variables into a `.env` file.

`PYANNOTE_TOKEN` is a token for pyannote.ai's services, which is what we use to handle diarization and speaker identification.<br>
`NGROK_TOKEN` is also required for pyannote.ai as they return results via a webhook/callback.<br>
`WIKI_USERNAME` and `WIKI_PASSWORD` are credentials for your bot account. You can create bot credentials at <https://www.sgutranscripts.org/wiki/Special:BotPasswords>.<br>
`OPENAI_API_KEY`, `OPENAI_ORGANIZATION`, and `OPENAI_PROJECT` are all used for calls to GPT.

Ruff and Pyright should be used for linting and type checking.
